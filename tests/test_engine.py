from pathlib import Path
from agent.excel_registry import ExcelWorkflowRegistry
from agent.router import WorkflowRouter
from agent.executor import WorkflowExecutor

ROOT=Path(__file__).parents[1]
reg=ExcelWorkflowRegistry(ROOT/"AI_Agent_Workflow_Assessment.xlsx")
router=WorkflowRouter(reg.all())
executor=WorkflowExecutor()

def test_registry_has_ten_workflows(): assert len(reg.all())==10

def test_router_examples():
    cases={"Which products need restocking?":"WF001","Find products where vendor price differs by more than 10%.":"WF002","Process this vendor spreadsheet and show invalid rows.":"WF003","Generate SEO content for this product.":"WF004","Where is order ORD-1001?":"WF005","Find likely duplicate products in the catalog.":"WF006","Create a campaign brief for the new collection.":"WF007","Classify these keywords and map them to pages.":"WF008","Assign this urgent task to the best available developer.":"WF009","Which workflows are failing most often?":"WF010"}
    for q,wid in cases.items(): assert router.route(q)[0].workflow_id==wid

def test_wf001():
    w=reg.get("WF001"); r=executor.execute(w,"Which products need restocking?",{"inventory_file":str(ROOT/"data/inventory.csv"),"selected_by":"test"})
    assert len(r.result["products_requiring_restock"])==2

def test_wf005():
    w=reg.get("WF005"); r=executor.execute(w,"Where is order ORD-1001?",{"order_id":"ORD-1001","selected_by":"test"})
    assert r.result["status"]=="Shipped"
