from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowDefinition:
    workflow_id: str
    name: str
    trigger: str
    inputs: str
    steps: list[str]
    decision_logic: str
    tools_required: list[str]
    expected_output: str


@dataclass
class ExecutionStep:
    number: int
    description: str
    status: str
    tool: str | None = None
    result: Any = None
    error: str | None = None
    duration: float | None = None


@dataclass
class ExecutionError:
    code: str
    message: str
    step: str | None = None
    recoverable: bool = False


@dataclass
class ExecutionResult:
    workflow_id: str
    workflow_name: str
    selected_by: str
    request: str
    steps: list[ExecutionStep] = field(default_factory=list)
    result: Any = None
    errors: list[ExecutionError] = field(default_factory=list)
    status: str = "running"
    execution_time: float = 0.0