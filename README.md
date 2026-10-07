# AI Agent Workflow Automation

A reusable, Excel-driven AI workflow engine for the 10 business workflows in the technical assessment.

## Architecture

```text
User Request
    |
    v
Single Agent Entry Point
    |
    v
Workflow Router -----> Excel Workflow Registry
    |                         |
    |                    10 workflow definitions
    v
Reusable Execution Engine
    |
    +--> Validation tools
    +--> CSV/XLSX reader
    +--> Calculator
    +--> Similarity
    +--> Order/shipment simulator
    +--> Employee ranking
    +--> LLM generation/classification
    |
    v
Execution Trace + Final Result
```

### Why this architecture

The Excel file is the business-level workflow registry. The system does **not** create 10 chatbots. One router selects a workflow, one execution engine runs it, and a shared tool layer performs operations.

Adding a new workflow with existing capabilities is primarily a data change: add a row to `Workflows` and provide the required input/tool context. A genuinely new capability requires one reusable tool operation, not another chatbot/agent.

### LLM role vs deterministic execution

The LLM is used where language reasoning adds value: workflow selection and content generation. Business-critical calculations and decisions such as `stock < threshold`, `price difference > 10%`, missing required fields, duplicate SKU detection, and employee ranking are deterministic. This reduces hallucination risk and makes tests reproducible.

## Project structure

```text
.
├── AI_Agent_Workflow_Assessment.xlsx   # supplied assessment source
├── app.py                              # FastAPI application
├── cli.py                              # CLI runner
├── requirements.txt
├── .env.example
├── agent/
│   ├── excel_registry.py               # Excel -> WorkflowDefinition
│   ├── router.py                       # LLM router + deterministic fallback
│   ├── executor.py                     # shared execution engine
│   └── models.py
├── tools/
│   ├── common.py                       # data/calculation primitives
│   ├── llm.py                          # LLM abstraction
│   └── simulators.py                   # order + employee API simulations
├── data/                               # reproducible sample inputs
└── tests/
```

## Setup

Python 3.11+ recommended.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
# .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

For LLM routing/content generation, add `OPENAI_API_KEY` to `.env`. Without a key, routing falls back to deterministic keyword routing and LLM-specific steps return a safe unavailable message; the deterministic workflows remain runnable.

## Run

API:

```bash
uvicorn app:app --reload
```

Then open `/docs` for Swagger UI.

CLI:

```bash
python cli.py "Which products need restocking?" --context '{"inventory_file":"data/inventory.csv"}'
```

Example API request:

```json
{
  "request": "Which products need restocking?",
  "context": {
    "inventory_file": "data/inventory.csv"
  }
}
```

The response contains:

- selected workflow
- routing method/confidence
- ordered execution trace
- tool used for each step
- final result
- errors, if any

## The 10 workflows

| ID | Workflow | Core decision |
|---|---|---|
| WF001 | Inventory Restock Check | current stock < minimum stock |
| WF002 | Product Price Validation | difference > 10% |
| WF003 | Vendor File Processing | missing SKU/product name = invalid |
| WF004 | Product Description Generator | never invent missing attributes |
| WF005 | Customer Order Status | not found -> request another identifier |
| WF006 | Duplicate Product Detection | exact SKU = definite; high similarity = possible |
| WF007 | Marketing Campaign Brief | missing goal/dates -> request input |
| WF008 | SEO Keyword Classification | intent classification |
| WF009 | Employee Task Assignment | skills + available capacity |
| WF010 | Workflow Performance Report | failure rate > 10% flagged |

## Test the assessment requests

```bash
pytest -q
```

The tests include all 10 supplied test questions for workflow routing and representative execution tests.

## Production considerations

**Reliability:** deterministic business rules are separated from LLM calls; every execution returns a trace and captures errors.

**Scalability:** workflow definitions are loaded from Excel into a registry; execution uses reusable tools. In production, the registry can be migrated to a database/config service without changing the execution contract.

**Latency/cost:** route once, then use deterministic tools wherever possible. LLM calls are isolated to language-heavy tasks.

**Security:** never put secrets in Excel; use environment/secret management. Validate uploaded files, enforce size/type limits, sandbox file processing, and authenticate the API.

**Observability:** the `ExecutionResult` structure is intentionally suitable for persistence to an execution-log table. WF010 consumes the same shape of execution logs for performance analysis.

## Interview / Loom talking points

1. I deliberately avoided ten separate agents because their routing, error handling, logging, and tool execution would be duplicated.
2. Excel is treated as the business workflow contract.
3. The LLM decides *which workflow* and generates language-heavy content; deterministic code owns business-critical calculations.
4. Every run produces an auditable trace: selected workflow -> steps -> tools -> outputs/errors.
5. The architecture supports an 11th workflow without creating another chatbot. If it uses existing tools, the new workflow can be represented as configuration; if it introduces a new capability, add one reusable tool rather than a new agent.

## Limitations / honest scope

The assessment does not provide live business APIs or a detailed tool schema beyond the Excel sheet. Therefore order/shipment and employee/task systems are simulated, while file-processing workflows use real sample CSVs. The README and Loom should explicitly call this out rather than implying production integrations exist.
