import os, json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
from agent.excel_registry import ExcelWorkflowRegistry
from agent.router import WorkflowRouter
from agent.executor import WorkflowExecutor
from tools.llm import LLMTool

load_dotenv()
BASE=Path(__file__).parent
registry=ExcelWorkflowRegistry(BASE / os.getenv("WORKFLOW_FILE","AI_Agent_Workflow_Assessment.xlsx"))
client=OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if (os.getenv("OPENAI_API_KEY") and OpenAI) else None
model=os.getenv("OPENAI_MODEL","gpt-5-mini")
router=WorkflowRouter(registry.all(),client,model)
llm=LLMTool(client,model)
executor=WorkflowExecutor(llm)
app=FastAPI(title="AI Agent Workflow Automation", version="1.0.0")

class RunRequest(BaseModel):
    request: str
    context: dict = Field(default_factory=dict)

@app.get("/")
def home():
    from fastapi.responses import HTMLResponse
    return HTMLResponse((BASE / "static_ui.html").read_text())

@app.get("/health")
def health(): return {"status":"ok","workflows":len(registry.all()),"llm_enabled":bool(client)}

@app.get("/workflows")
def workflows():
    return [{"id":w.workflow_id,"name":w.name,"trigger":w.trigger,"tools":w.tools_required,"steps":w.steps} for w in registry.all()]

@app.post("/run")
def run(body: RunRequest):
    workflow, selected_by, routing=router.route(body.request)
    context=dict(body.context); context["selected_by"]=selected_by
    result=executor.execute(workflow,body.request,context)
    return {"selected_workflow":{"id":workflow.workflow_id,"name":workflow.name,"routing":routing,"selected_by":selected_by},"request":body.request,"steps_executed":[s.__dict__ for s in result.steps],"result":result.result,"errors":result.errors}

