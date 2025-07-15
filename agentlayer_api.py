# agentlayer/api.py

import os
import json
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# Import custom modules
from . import rule_checker
from . import llm_agent
from . import logger
from . import langflow # LangGraph workflow

app = FastAPI(
    title="AgentLayer Constitution API",
    description="API for running AI agents with constitution validation and logging.",
    version="1.0.0"
)

# ✅ Fly.io Health Check용 루트 라우트
@app.get("/", summary="Health Check")
async def root():
    return {"message": "🟢 Fly.io FastAPI 서버 작동 중"}

# FastAPI 애플리케이션 종료 시 httpx 클라이언트 종료
@app.on_event("shutdown")
async def shutdown_event():
    await llm_agent.client.aclose()
    print("HTTPX client closed.")

# Ensure the agentlayer directory exists for logs and constitution.json
os.makedirs("agentlayer", exist_ok=True)

# Ensure initial constitution.json and log.json are present
initial_constitution_path = "agentlayer/constitution.json"
initial_log_path = "agentlayer/log.json"

if not os.path.exists(initial_constitution_path):
    with open(initial_constitution_path, "w", encoding="utf-8") as f:
        f.write("""
{
    "rules": [
        {"id": "R1", "type": "keyword", "keywords": ["sudo", "rm -rf", "nuke", "delete files"], "severity": "high"},
        {"id": "R2", "type": "role", "allowed_roles": ["developer", "analyst"], "severity": "medium"},
        {"id": "R3", "type": "keyword", "keywords": ["unethical", "harmful"], "severity": "critical"}
    ]
}
        """)

if not os.path.exists(initial_log_path):
    with open(initial_log_path, "w", encoding="utf-8") as f:
        f.write("[]")

# Pydantic Input Model for /run endpoint
class RunRequest(BaseModel):
    input_text: str
    role: Optional[str] = "developer"
    llm_model: Optional[str] = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free"

# Pydantic Response Model
class RunResponse(BaseModel):
    uuid: str
    timestamp: str
    input: str
    output: str
    role: str
    llm_model: str
    violations: List[Dict[str, Any]]
    score: int

# Build the LangGraph workflow
agent_workflow = langflow.build_agent_workflow()

@app.post("/run", response_model=RunResponse, summary="Run Agent with Constitution Check")
async def run_agent(request: RunRequest):
    log_id = str(uuid4())
    timestamp = datetime.utcnow().isoformat()

    initial_state: langflow.AgentFlowState = {
        "input_text": request.input_text,
        "output_text": None,
        "role": request.role,
        "llm_model": request.llm_model,
        "log_id": log_id,
        "timestamp": timestamp,
        "violations": [],
        "score": 100
    }

    print(f"Starting LangGraph workflow for UUID: {log_id}")
    final_state = await agent_workflow.invoke(initial_state)
    print(f"Completed LangGraph workflow for UUID: {log_id}")

    return JSONResponse(content={
        "uuid": final_state["log_id"],
        "timestamp": final_state["timestamp"],
        "input": final_state["input_text"],
        "output": final_state["output_text"] or "",
        "role": final_state["role"],
        "llm_model": final_state["llm_model"],
        "violations": final_state["violations"],
        "score": final_state["score"]
    })

@app.get("/score", summary="Get Overall Constitution Score")
async def get_overall_score():
    logs = logger.load_logs()
    if not logs:
        return {"total_runs": 0, "average_score": 100, "violation_summary": {}}

    total_score_sum = sum(log.get("score", 0) for log in logs)
    average_score = total_score_sum / len(logs)

    violation_counts = {}
    for log in logs:
        for violation in log.get("violations", []):
            rule_id = violation.get("rule_id", "unknown")
            violation_counts[rule_id] = violation_counts.get(rule_id, 0) + 1

    return {
        "total_runs": len(logs),
        "average_score": round(average_score, 2),
        "violation_summary": violation_counts
    }

@app.get("/trace/{trace_uuid}", summary="Trace Specific Agent Execution")
async def trace_execution(trace_uuid: str):
    logs = logger.load_logs()
    for log in logs:
        if log.get("uuid") == trace_uuid:
            return JSONResponse(content=log)
    raise HTTPException(status_code=404, detail=f"Log with UUID '{trace_uuid}' not found.")

@app.get("/report", response_class=HTMLResponse, summary="Generate HTML Report of Executions")
async def generate_report():
    logs = logger.load_logs()
    html_content = """..."""  # 그대로 유지

    return HTMLResponse(content=html_content)

# ✅ 로컬 실행용 설정 (포트 8080 고정)
if __name__ == "__main__":
    os.environ.setdefault("TOGETHER_API_KEY", "YOUR_TOGETHER_API_KEY_HERE")
    print("Running FastAPI app on http://0.0.0.0:8080")
    uvicorn.run("agentlayer.api:app", host="0.0.0.0", port=8080)
