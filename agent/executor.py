import re
import time
from pathlib import Path
import pandas as pd
from .models import ExecutionResult, ExecutionStep, ExecutionError
from tools.common import read_table, normalize_columns, pct_difference, similarity
from tools.simulators import lookup_order, rank_employee


class WorkflowExecutor:

    def __init__(self, llm=None):
        self.llm = llm

    def execute(self, workflow, request: str, context: dict | None = None):
        context = context or {}
        start_time = time.perf_counter()

        result = ExecutionResult(
            workflow.workflow_id,
            workflow.name,
            context.get("selected_by", "unknown"),
            request,
        )

        try:
            self.validate_inputs(
                workflow.workflow_id,
                context,
                result
            )

            fn = getattr(
                self,
                f"run_{workflow.workflow_id.lower()}"
            )

            output = fn(request, context, result)
            result.result = output
            result.status = "success"

        except Exception as e:
            result.status = "failed"
            result.errors.append(
                ExecutionError(
                    code="WORKFLOW_EXECUTION_ERROR",
                    message=str(e),
                    step=workflow.workflow_id,
                    recoverable=False,
                )
            )

        finally:
            result.execution_time = round(
                time.perf_counter() - start_time,
                4
            )

        return result

    def validate_inputs(self, workflow_id, context, result):
        required_inputs = {
            "WF001": ["inventory_file"],
            "WF002": ["product_file", "vendor_file"],
            "WF003": ["vendor_file"],
            "WF004": [],
            "WF005": [],
            "WF006": ["catalog_file"],
            "WF007": ["campaign_goal", "dates"],
            "WF008": ["keyword_file"],
            "WF009": [],
            "WF010": ["logs_file"],
        }

        required = required_inputs.get(workflow_id, [])

        missing = [
            key for key in required
            if not context.get(key)
        ]

        if missing:
            raise ValueError(
                f"Missing required inputs for {workflow_id}: {missing}"
            )

        result.steps.append(
            ExecutionStep(
                len(result.steps) + 1,
                "Validate workflow inputs",
                "success",
                "input validator",
                {"validated": required},
                duration=0.0,
            )
        )

    def step(self, result, description, fn, tool=None):
        n = len(result.steps) + 1
        start_time = time.perf_counter()

        try:
            value = fn()

            duration = round(
                time.perf_counter() - start_time,
                4
            )

            result.steps.append(
                ExecutionStep(
                    n,
                    description,
                    "success",
                    tool,
                    value,
                    duration=duration,
                )
            )

            return value

        except Exception as e:
            duration = round(
                time.perf_counter() - start_time,
                4
            )

            result.steps.append(
                ExecutionStep(
                    n,
                    description,
                    "failed",
                    tool,
                    error=str(e),
                    duration=duration,
                )
            )

            raise

    def run_wf001(self, request, c, r):
        df = self.step(
            r,
            "Load inventory",
            lambda: read_table(c["inventory_file"]),
            "CSV reader"
        )

        df = normalize_columns(df)

        self.step(
            r,
            "Compare current stock with minimum threshold",
            lambda: True,
            "calculator"
        )

        required = {
            "sku",
            "product_name",
            "current_stock",
            "minimum_stock"
        }

        if not required <= set(df.columns):
            raise ValueError(
                f"Inventory missing columns: "
                f"{sorted(required - set(df.columns))}"
            )

        low = df[
            df.current_stock < df.minimum_stock
        ].copy()

        low["suggested_reorder_quantity"] = (
            low.minimum_stock - low.current_stock
        )

        self.step(
            r,
            "Identify low-stock products and calculate reorder quantity",
            lambda: low.to_dict("records"),
            "calculator"
        )

        return {
            "products_requiring_restock":
                low[
                    [
                        "sku",
                        "product_name",
                        "current_stock",
                        "minimum_stock",
                        "suggested_reorder_quantity",
                    ]
                ].to_dict("records")
        }

    def run_wf002(self, request, c, r):
        p = self.step(
            r,
            "Load product prices",
            lambda: normalize_columns(
                read_table(c["product_file"])
            ),
            "CSV reader"
        )

        v = self.step(
            r,
            "Load vendor prices",
            lambda: normalize_columns(
                read_table(c["vendor_file"])
            ),
            "CSV reader"
        )

        if "sku" not in p or "sku" not in v:
            raise ValueError("Both files require sku")

        m = p.merge(
            v,
            on="sku",
            suffixes=("_internal", "_vendor")
        )

        if "price_internal" not in m or "price_vendor" not in m:
            raise ValueError("Both files require price")

        m["difference_percent"] = m.apply(
            lambda x: pct_difference(
                x.price_internal,
                x.price_vendor
            ),
            axis=1
        )

        flagged = m[m.difference_percent > 10]

        self.step(
            r,
            "Match SKUs and calculate percentage differences",
            lambda: len(m),
            "calculator"
        )

        self.step(
            r,
            "Flag exceptions above 10%",
            lambda: len(flagged),
            "calculator"
        )

        return {
            "matched_products": m.to_dict("records"),
            "exceptions": flagged.to_dict("records")
        }

    def run_wf003(self, request, c, r):
        df = self.step(
            r,
            "Read vendor file",
            lambda: normalize_columns(
                read_table(c["vendor_file"])
            ),
            "Excel/CSV parser"
        )

        self.step(
            r,
            "Detect and normalize columns",
            lambda: list(df.columns),
            "data validation"
        )

        invalid = df[
            df.get(
                "sku",
                pd.Series([None] * len(df))
            ).isna()
            |
            df.get(
                "product_name",
                pd.Series([None] * len(df))
            ).isna()
        ]

        clean = df.drop(invalid.index)

        self.step(
            r,
            "Validate required fields and identify invalid rows",
            lambda: len(invalid),
            "data validation"
        )

        return {
            "cleaned_dataset": clean.to_dict("records"),
            "invalid_rows": invalid.to_dict("records"),
            "summary": {
                "valid": len(clean),
                "invalid": len(invalid)
            }
        }

    def run_wf004(self, request, c, r):
        required = [
            "product_name",
            "category",
            "attributes",
            "material",
            "color",
            "target_audience"
        ]

        missing = [
            x for x in required
            if not c.get(x)
        ]

        self.step(
            r,
            "Validate required attributes",
            lambda: missing,
            "text validation"
        )

        data = {
            k: c.get(k)
            for k in required
        }

        prompt = (
            "Create product description, short description, "
            "SEO title and meta description. "
            "Do not invent missing attributes; explicitly mark them. "
            "Data: " + str(data)
        )

        out = self.step(
            r,
            "Generate product content",
            lambda:
                self.llm.generate(
                    "You are a careful ecommerce copywriter.",
                    prompt
                )
                if self.llm
                else "LLM unavailable",
            "LLM"
        )

        return {
            "missing_attributes": missing,
            "content": out
        }

    def run_wf005(self, request, c, r):
        match = re.search(
            r"ORD[- ]?\d+",
            request,
            re.I
        )

        oid = (
            c.get("order_id")
            or (
                match.group(0)
                .upper()
                .replace(" ", "")
                if match
                else None
            )
        )

        self.step(
            r,
            "Validate order identifier",
            lambda: oid,
            "validation"
        )

        order = self.step(
            r,
            "Search order data",
            lambda: lookup_order(
                oid,
                c.get("email")
            ),
            "Order database/API"
        )

        if not order:
            return {
                "status": "not_found",
                "message":
                    "No order found. Please provide another "
                    "order ID or customer email."
            }

        self.step(
            r,
            "Retrieve shipment information",
            lambda: order.get("shipment_status"),
            "shipment lookup"
        )

        return {
            "order_id": oid,
            **order
        }

    def run_wf006(self, request, c, r):
        df = self.step(
            r,
            "Load product catalog",
            lambda: normalize_columns(
                read_table(c["catalog_file"])
            ),
            "CSV/database reader"
        )

        groups = []
        seen = set()

        for i, row in df.iterrows():
            if i in seen:
                continue

            group = [i]
            definite = []
            possible = []

            for j, row2 in df.iterrows():
                if j <= i or j in seen:
                    continue

                if (
                    "sku" in df
                    and pd.notna(row.get("sku"))
                    and pd.notna(row2.get("sku"))
                    and str(row.sku).strip()
                    == str(row2.sku).strip()
                ):
                    group.append(j)
                    definite.append(j)
                else:
                    sim = similarity(
                        row.get("product_name", ""),
                        row2.get("product_name", "")
                    )

                    if sim >= 0.90:
                        group.append(j)
                        possible.append((j, sim))

            if len(group) > 1:
                seen.update(group)

                groups.append({
                    "products":
                        df.loc[group].to_dict("records"),
                    "confidence":
                        "definite"
                        if definite
                        else "possible",
                    "similarity":
                        round(
                            max(
                                [x[1] for x in possible],
                                default=1
                            ),
                            3
                        )
                })

        self.step(
            r,
            "Normalize identifiers and compare attributes",
            lambda: len(groups),
            "text similarity"
        )

        return {
            "duplicate_groups": groups
        }

    def run_wf007(self, request, c, r):
        missing = [
            x
            for x in ["campaign_goal", "dates"]
            if not c.get(x)
        ]

        self.step(
            r,
            "Validate campaign inputs",
            lambda: missing,
            "validation"
        )

        if missing:
            return {
                "status": "needs_input",
                "missing": missing,
                "message":
                    "Please provide campaign goal and dates "
                    "before generation."
            }

        prompt = (
            f"Create structured campaign brief. "
            f"Inputs: {c}"
        )

        out = self.step(
            r,
            "Generate messaging, channels and checklist",
            lambda:
                self.llm.generate(
                    "You are a marketing strategist. "
                    "Return structured concise output.",
                    prompt
                )
                if self.llm
                else "LLM unavailable",
            "LLM"
        )

        return {
            "brief": out
        }

    def run_wf008(self, request, c, r):
        df = self.step(
            r,
            "Read keywords",
            lambda: normalize_columns(
                read_table(c["keyword_file"])
            ),
            "CSV reader"
        )

        if "keyword" not in df:
            raise ValueError(
                "Keyword file requires keyword column"
            )

        df = df.drop_duplicates(
            subset=["keyword"]
        ).copy()

        def classify(k):
            q = str(k).lower()

            if any(
                x in q
                for x in ["how", "what", "guide", "meaning"]
            ):
                return "informational"

            if any(
                x in q
                for x in ["buy", "price", "deal", "discount"]
            ):
                return "transactional"

            if any(
                x in q
                for x in ["best", "top", "compare", "review"]
            ):
                return "commercial"

            return "navigational"

        df["intent"] = df.keyword.map(classify)

        df["priority"] = df.intent.map(
            lambda x:
                "high"
                if x in {"transactional", "commercial"}
                else "medium"
        )

        df["recommended_target_page"] = df.intent.map(
            lambda x: {
                "informational": "blog/guide",
                "commercial": "category/comparison",
                "transactional": "product/landing",
                "navigational": "brand/home"
            }[x]
        )

        self.step(
            r,
            "Classify intent and map categories",
            lambda: len(df),
            "LLM/classifier"
        )

        return {
            "keyword_report":
                df.to_dict("records")
        }

    def run_wf009(self, request, c, r):
        skills = c.get("skills", [])
        priority = c.get(
            "priority",
            "normal"
        )

        self.step(
            r,
            "Understand task requirements",
            lambda: {
                "skills": skills,
                "priority": priority
            },
            "task parser"
        )

        ranked = self.step(
            r,
            "Compare skills and workload",
            lambda: rank_employee(
                skills,
                priority
            ),
            "ranking logic"
        )

        if (
            not ranked
            or ranked[0]["score"] < 0.35
        ):
            return {
                "status": "escalate",
                "message":
                    "No suitable employee with required "
                    "skills and capacity."
            }

        chosen = ranked[0]

        return {
            "recommended_employee":
                chosen["name"],
            "reasoning":
                f"Skill/capacity score {chosen['score']}",
            "priority": priority,
            "deadline": c.get("deadline"),
            "task": c.get("task_description")
        }

    def run_wf010(self, request, c, r):
        df = self.step(
            r,
            "Load workflow execution logs",
            lambda: normalize_columns(
                read_table(c["logs_file"])
            ),
            "CSV/database reader"
        )

        required = {
            "workflow_id",
            "status",
            "execution_time"
        }

        if not required <= set(df.columns):
            raise ValueError(
                f"Logs missing columns: "
                f"{sorted(required - set(df.columns))}"
            )

        summary = (
            df.groupby("workflow_id")
            .agg(
                executions=("status", "size"),
                failures=(
                    "status",
                    lambda x:
                        (x.str.lower() == "failed").sum()
                ),
                avg_execution_time=(
                    "execution_time",
                    "mean"
                )
            )
            .reset_index()
        )

        summary["failure_rate"] = (
            summary.failures
            / summary.executions
            * 100
        )

        summary["flag"] = (
            summary.failure_rate > 10
        )

        self.step(
            r,
            "Calculate success/failure rate and average execution time",
            lambda: len(summary),
            "calculator"
        )

        return {
            "summary":
                summary.to_dict("records"),
            "recommendations": [
                "Investigate workflows flagged above the 10% failure threshold.",
                "Profile slow steps and add caching/batching where appropriate."
            ]
        }