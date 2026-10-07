import json
import re
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = object

from .models import WorkflowDefinition


class WorkflowRouter:
    """LLM router with a deterministic fallback.

    The LLM receives only workflow metadata and returns one workflow ID.
    Execution remains deterministic and tool-driven after routing.
    """

    def __init__(
        self,
        workflows: list[WorkflowDefinition],
        client: OpenAI | None = None,
        model: str = "gpt-5-mini",
    ):
        self.workflows = workflows
        self.client = client
        self.model = model

    def route(self, request: str) -> tuple[WorkflowDefinition, str, dict[str, Any]]:
        if self.client:
            try:
                catalog = [
                    {
                        "id": w.workflow_id,
                        "name": w.name,
                        "trigger": w.trigger,
                        "inputs": w.inputs,
                        "expected_output": w.expected_output,
                    }
                    for w in self.workflows
                ]

                prompt = (
                    "Select exactly one workflow for the user's request. "
                    'Return JSON only: {"workflow_id":"WFxxx",'
                    '"confidence":0.0,"reason":"..."}.'
                    f"\nWorkflows: {json.dumps(catalog)}"
                    f"\nUser request: {request}"
                )

                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                )

                text = response.output_text.strip()
                data = json.loads(text)

                chosen = next(
                    w for w in self.workflows
                    if w.workflow_id == data["workflow_id"]
                )

                # Accept LLM routing only when confidence is high enough.
                if data.get("confidence", 0) >= 0.65:
                    return chosen, "llm", data

            except Exception as e:
                print(f"\n[LLM ROUTER ERROR] {type(e).__name__}: {e}\n")

        # Fall back to deterministic routing if LLM fails
        # or its confidence is too low.
        return self._heuristic_route(request)

    def _heuristic_route(self, request: str):
        q = request.lower()
        scores = []

        keywords = {
            "WF001": [
                "restock", "restocking", "low stock",
                "reorder", "inventory"
            ],
            "WF002": [
                "price", "vendor price",
                "price difference", "pricing"
            ],
            "WF003": [
                "vendor file", "vendor spreadsheet",
                "cleaned dataset", "invalid rows",
                "process this file"
            ],
            "WF004": [
                "description", "seo content",
                "product content", "meta description",
                "seo title"
            ],
            "WF005": [
                "order", "tracking", "shipment",
                "where is order", "order status"
            ],
            "WF006": [
                "duplicate", "duplicates",
                "similar products", "duplicate products"
            ],
            "WF007": [
                "campaign brief", "campaign",
                "marketing brief", "messaging"
            ],
            "WF008": [
                "keyword", "keywords",
                "search intent", "classify keywords"
            ],
            "WF009": [
                "assign", "employee",
                "developer", "workload", "task"
            ],
            "WF010": [
                "performance report", "failing most",
                "failure rate", "execution time",
                "workflow performance"
            ],
        }

        for wid, terms in keywords.items():
            scores.append(
                (sum(1 for t in terms if t in q), wid)
            )

        score, wid = max(scores)

        if score == 0:
            wid = "WF010" if "workflow" in q else "WF001"

        return (
            next(w for w in self.workflows if w.workflow_id == wid),
            "heuristic",
            {
                "confidence": min(score / 3, 1.0),
                "reason": "keyword fallback",
            },
        )