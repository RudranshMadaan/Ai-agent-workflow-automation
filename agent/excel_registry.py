from pathlib import Path
import openpyxl
from .models import WorkflowDefinition

class ExcelWorkflowRegistry:

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.workflows = self._load()

    def _load(self) -> dict[str, WorkflowDefinition]:
        wb = openpyxl.load_workbook(self.path, data_only=True)
        ws = wb["Workflows"]
        result = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]:
                continue
            steps = [s.strip() for s in str(row[4]).split("→")]
            tools = [s.strip() for s in str(row[6]).split(";")]
            result[str(row[0])] = WorkflowDefinition(
                workflow_id=str(row[0]), name=str(row[1]), trigger=str(row[2]),
                inputs=str(row[3]), steps=steps, decision_logic=str(row[5]),
                tools_required=tools, expected_output=str(row[7])
            )
        return result

    def all(self):
        return list(self.workflows.values())

    def get(self, workflow_id: str):
        return self.workflows[workflow_id]
