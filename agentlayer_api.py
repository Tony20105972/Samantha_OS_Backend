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
    role: Optional[str] = "developer" # Default role
    llm_model: Optional[str] = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free" # Default to DeepSeek Free

# Pydantic Response Model for /run endpoint
class RunResponse(BaseModel):
    uuid: str
    timestamp: str
    input: str
    output: str
    role: str
    llm_model: str
    violations: List[Dict[str, Any]]
    score: int

# Build the LangGraph workflow once
agent_workflow = langflow.build_agent_workflow()

@app.post("/run", response_model=RunResponse, summary="Run Agent with Constitution Check")
async def run_agent(request: RunRequest):
    """
    Runs an AI agent with the given input and role, applies constitution checks,
    and logs the execution using the LangGraph workflow.
    """
    log_id = str(uuid4())
    timestamp = datetime.utcnow().isoformat()

    # Initial state for LangGraph workflow
    initial_state: langflow.AgentFlowState = {
        "input_text": request.input_text,
        "output_text": None, # Will be filled by LLM node
        "role": request.role,
        "llm_model": request.llm_model,
        "log_id": log_id,
        "timestamp": timestamp,
        "violations": [], # Will be filled by constitution_check node
        "score": 100 # Will be filled by constitution_check node
    }

    print(f"Starting LangGraph workflow for UUID: {log_id}")
    final_state = await agent_workflow.invoke(initial_state)
    print(f"Completed LangGraph workflow for UUID: {log_id}")

    # The final_state now contains all processed information
    return JSONResponse(content={
        "uuid": final_state["log_id"],
        "timestamp": final_state["timestamp"],
        "input": final_state["input_text"],
        "output": final_state["output_text"] or "", # Ensure it's not None
        "role": final_state["role"],
        "llm_model": final_state["llm_model"],
        "violations": final_state["violations"],
        "score": final_state["score"]
    })

@app.get("/score", summary="Get Overall Constitution Score")
async def get_overall_score():
    """
    Calculates and returns the overall constitution score based on all logged executions.
    """
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
    """
    Retrieves the details of a specific agent execution using its UUID.
    """
    logs = logger.load_logs()
    for log in logs:
        if log.get("uuid") == trace_uuid:
            return JSONResponse(content=log)
    raise HTTPException(status_code=404, detail=f"Log with UUID '{trace_uuid}' not found.")

@app.get("/report", response_class=HTMLResponse, summary="Generate HTML Report of Executions")
async def generate_report():
    """
    Generates an HTML report summarizing all agent executions and their constitution compliance.
    """
    logs = logger.load_logs()

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AgentLayer Execution Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
            .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1, h2 { color: #0056b3; }
            .log-entry {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 15px;
                background-color: #f9f9f9;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }
            .log-entry.violated { border-left: 5px solid #dc3545; }
            .log-entry.compliant { border-left: 5px solid #28a745; }
            .log-entry h3 { margin-top: 0; color: #007bff; }
            .log-entry p { margin: 5px 0; }
            .violations-list { list-style-type: none; padding: 0; }
            .violations-list li { background-color: #ffebe6; border-left: 3px solid #dc3545; margin-bottom: 5px; padding: 8px; border-radius: 3px; }
            .metadata { font-size: 0.9em; color: #666; }
            .score { font-weight: bold; }
            .score.pass { color: #28a745; }
            .score.fail { color: #dc3545; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AgentLayer Execution Report</h1>
            <p class="metadata">Generated on: """ + datetime.utcnow().isoformat() + """</p>
            <h2>Total Runs: """ + str(len(logs)) + """</h2>
            """
    if logs:
        for log in logs:
            is_violated = "violated" if log.get("violations") else "compliant"
            score_class = "pass" if log.get("score", 100) > 70 else "fail" # Example threshold
            html_content += f"""
            <div class="log-entry {is_violated}">
                <h3>Execution UUID: {log.get('uuid', 'N/A')}</h3>
                <p class="metadata">Timestamp: {log.get('timestamp', 'N/A')}</p>
                <p><strong>Agent Role:</strong> {log.get('role', 'N/A')}</p>
                <p><strong>LLM Model:</strong> {log.get('llm_model', 'N/A')}</p>
                <p><strong>Input:</strong> {log.get('input', 'N/A')}</p>
                <p><strong>Output:</strong> {log.get('output', 'N/A')}</p>
                <p><strong>Score:</strong> <span class="score {score_class}">{log.get('score', 'N/A')} / 100</span></p>
            """
            if log.get('violations'):
                html_content += """
                <p><strong>Violations:</strong></p>
                <ul class="violations-list">
                """
                for violation in log['violations']:
                    html_content += f"""
                    <li>
                        Rule ID: {violation.get('rule_id', 'N/A')},
                        Type: {violation.get('type', 'N/A')},
                        Trigger: "{violation.get('trigger', 'N/A')}",
                        Severity: {violation.get('severity', 'N/A')}
                    </li>
                    """
                html_content += """
                </ul>
                """
            else:
                html_content += """
                <p><strong>Violations:</strong> None</p>
                """
            html_content += """
            </div>
            """
    else:
        html_content += "<p>No execution logs found.</p>"

    html_content += """
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# For local development:
# if __name__ == "__main__":
#     # Set a dummy API key for local testing if not already set
#     os.environ.setdefault("TOGETHER_API_KEY", "YOUR_TOGETHER_API_KEY_HERE")
#     print("Running FastAPI app locally on http://127.0.0.1:8000")
#     print("Access API Docs at http://127.0.0.1:8000/docs")
#     uvicorn.run("agentlayer.api:app", host="0.0.0.0", port=8000, reload=True)
