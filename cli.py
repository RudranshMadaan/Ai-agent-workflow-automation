import argparse, json
from app import router, executor
p=argparse.ArgumentParser(); p.add_argument("request"); p.add_argument("--context",default="{}")
a=p.parse_args(); workflow,selected_by,routing=router.route(a.request); c=json.loads(a.context); c["selected_by"]=selected_by
r=executor.execute(workflow,a.request,c)
print(json.dumps({"selected_workflow":{"id":workflow.workflow_id,"name":workflow.name,"routing":routing,"selected_by":selected_by},"steps_executed":[s.__dict__ for s in r.steps],"result":r.result,"errors":r.errors},indent=2,default=str))
