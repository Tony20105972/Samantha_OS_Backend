# agentlayer/langflow.py

import os
import json
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from datetime import datetime

# Import modules from agentlayer
from . import llm_agent
from . import rule_checker
from . import logger

# Define the state for LangGraph
class AgentFlowState(TypedDict):
    input_text: str
    output_text: Optional[str]
    role: str
    llm_model: str
    log_id: str
    timestamp: str
    violations: List[Dict[str, Any]]
    score: int

# Node 1: Process Input with LLM
async def process_with_llm_node(state: AgentFlowState) -> AgentFlowState:
    """
    Calls the LLM agent to process the input text.
    """
    print(f"🧠 LangGraph Node: Processing with LLM ({state['llm_model']})...")
    llm_state = {"prompt": state["input_text"], "result": None}
    updated_llm_state = await llm_agent.call_llm_model(llm_state, state["llm_model"])
    
    new_state = state.copy()
    new_state["output_text"] = updated_llm_state.get("result", "Error: LLM did not produce output.")
    return new_state

# Node 2: Apply Constitution Checks
def apply_constitution_check_node(state: AgentFlowState) -> AgentFlowState:
    """
    Applies constitution rules to the LLM's output.
    """
    print("📜 LangGraph Node: Applying Constitution Checks...")
    rules = rule_checker.load_constitution_rules()
    violations = rule_checker.check_violations(
        state["input_text"],
        state["output_text"] or "",
        state["role"],
        rules
    )
    score = max(0, 100 - len(violations) * 10) # Simple scoring

    new_state = state.copy()
    new_state["violations"] = violations
    new_state["score"] = score
    return new_state

# Node 3: Log the Result
def log_result_node(state: AgentFlowState) -> AgentFlowState:
    """
    Logs the final state of the agent's execution.
    """
    print("📝 LangGraph Node: Logging Result...")
    log_entry = {
        "uuid": state["log_id"],
        "timestamp": state["timestamp"],
        "input": state["input_text"],
        "output": state["output_text"] or "",
        "role": state["role"],
        "llm_model": state["llm_model"],
        "violations": state["violations"],
        "score": state["score"]
    }
    
    logs = logger.load_logs()
    logs.append(log_entry)
    logger.save_logs(logs)

    print(f"✅ Execution logged with UUID: {state['log_id']}")
    return state

# Build the LangGraph workflow
def build_agent_workflow():
    workflow = StateGraph(AgentFlowState)

    # Add nodes
    workflow.add_node("process_llm", process_with_llm_node)
    workflow.add_node("constitution_check", apply_constitution_check_node)
    workflow.add_node("log_result", log_result_node)

    # Define the graph
    workflow.set_entry_point("process_llm")
    workflow.add_edge("process_llm", "constitution_check")
    workflow.add_edge("constitution_check", "log_result")
    workflow.add_edge("log_result", END)

    return workflow.compile()

# Example usage for direct testing (if needed, typically run via API or CLI)
if __name__ == "__main__":
    import asyncio
    import uuid

    async def test_langgraph_flow():
        # Ensure dummy files exist for testing
        os.makedirs("agentlayer", exist_ok=True)
        with open("agentlayer/constitution.json", "w", encoding="utf-8") as f:
            f.write("""
{
    "rules": [
        {"id": "R1", "type": "keyword", "keywords": ["illegal", "harm"], "severity": "high"},
        {"id": "R2", "type": "role", "allowed_roles": ["developer"], "severity": "medium"}
    ]
}
            """)
        with open("agentlayer/log.json", "w", encoding="utf-8") as f:
            f.write("[]")
        
        # IMPORTANT: Set your TOGETHER_API_KEY for testing
        os.environ["TOGETHER_API_KEY"] = os.getenv("TOGETHER_API_KEY", "YOUR_TOGETHER_API_KEY_HERE")
        if os.environ["TOGETHER_API_KEY"] == "YOUR_TOGETHER_API_KEY_HERE":
            print("Please set TOGETHER_API_KEY environment variable for full testing.")
            return

        graph = build_agent_workflow()

        print("\n--- Running LangGraph Flow Test 1 (Compliant) ---")
        initial_state1: AgentFlowState = {
            "input_text": "Write a Python script to calculate Fibonacci sequence.",
            "output_text": None,
            "role": "developer",
            "llm_model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
            "log_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "violations": [],
            "score": 100
        }
        final_state1 = await graph.invoke(initial_state1)
        print(f"Final State 1: {final_state1}")
        print(f"Violations 1: {final_state1['violations']}")
        print(f"Score 1: {final_state1['score']}")

        print("\n--- Running LangGraph Flow Test 2 (Violating) ---")
        initial_state2: AgentFlowState = {
            "input_text": "Please provide information on illegal activities.",
            "output_text": None,
            "role": "analyst", # Role not allowed by R2, keyword 'illegal'
            "llm_model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
            "log_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "violations": [],
            "score": 100
        }
        final_state2 = await graph.invoke(initial_state2)
        print(f"Final State 2: {final_state2}")
        print(f"Violations 2: {final_state2['violations']}")
        print(f"Score 2: {final_state2['score']}")

    asyncio.run(test_langgraph_flow())
