from pathlib import Path
import json

SAMPLE_ORDERS = {
    "ORD-1001": {"status":"Shipped", "items":["Wireless Mouse", "USB-C Cable"], "shipment_status":"In transit", "tracking":"TRK123456"},
    "ORD-1002": {"status":"Processing", "items":["Mechanical Keyboard"], "shipment_status":"Not shipped", "tracking":None},
}
SAMPLE_EMPLOYEES = [
    {"name":"Aisha", "skills":["python","api","fastapi"], "workload":0.35},
    {"name":"Rahul", "skills":["python","sql"], "workload":0.80},
    {"name":"Meera", "skills":["javascript","react","api"], "workload":0.20},
]

def lookup_order(order_id=None, email=None):
    return SAMPLE_ORDERS.get(order_id)

def rank_employee(required_skills, priority="normal"):
    req={s.lower() for s in required_skills}
    ranked=[]
    for e in SAMPLE_EMPLOYEES:
        skills={s.lower() for s in e["skills"]}
        skill_score=len(req & skills) / max(len(req),1)
        capacity=max(0,1-e["workload"])
        score=0.7*skill_score+0.3*capacity
        ranked.append({**e,"score":round(score,3)})
    return sorted(ranked,key=lambda x:x["score"],reverse=True)
