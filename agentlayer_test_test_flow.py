# agentlayer/test/test_flow.py

import pytest
import os
import json
import asyncio
from unittest.mock import AsyncMock, patch
from .. import langflow
from .. import llm_agent # To patch its methods
from .. import logger # To patch its methods
from .. import rule_checker # To patch its methods

# Fixture for setting up a temporary agentlayer directory with dummy files
@pytest.fixture
def temp_agentlayer_env(tmp_path):
    test_dir = tmp_path / "agentlayer"
    test_dir.mkdir()
    
    # Create dummy constitution.json
    constitution_path = test_dir / "constitution.json"
    with open(constitution_path, "w", encoding="utf-8") as f:
        json.dump({"rules": [
            {"id": "R1", "type": "keyword", "keywords": ["forbidden"], "severity": "high"},
            {"id": "R2", "type": "role", "allowed_roles": ["allowed_role"], "severity": "medium"}
        ]}, f)
    
    # Create dummy log.json
    log_path = test_dir / "log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump([], f)
    
    # Change current working directory to tmp_path for the test
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield
    os.chdir(original_cwd)

# Test the full LangGraph workflow
@pytest.mark.asyncio
@patch('agentlayer.llm_agent.call_llm_model') # Patch the actual LLM call
@patch('agentlayer.logger.save_logs') # Patch log saving
@patch('agentlayer.logger.load_logs') # Patch log loading
async def test_langgraph_flow_compliant(mock_load_logs, mock_save_logs, mock_call_llm_model, temp_agentlayer_env):
    # Mock LLM response
    mock_call_llm_model.return_value = {"prompt": "test", "result": "This is a compliant output."}
    mock_load_logs.return_value = [] # Start with empty logs

    graph = langflow.build_agent_workflow()

    initial_state = {
        "input_text": "Write a poem.",
        "output_text": None,
        "role": "allowed_role",
        "llm_model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
        "log_id": "test-uuid-compliant",
        "timestamp": datetime.utcnow().isoformat(),
        "violations": [],
        "score": 100
    }

    final_state = await graph.invoke(initial_state)

    # Assertions
    mock_call_llm_model.assert_called_once()
    assert final_state["output_text"] == "This is a compliant output."
    assert final_state["violations"] == []
    assert final_state["score"] == 100
    mock_save_logs.assert_called_once()
    saved_log = mock_save_logs.call_args[0][0][0] # Get the first log entry
    assert saved_log["uuid"] == "test-uuid-compliant"
    assert saved_log["violations"] == []
    assert saved_log["score"] == 100

@pytest.mark.asyncio
@patch('agentlayer.llm_agent.call_llm_model') # Patch the actual LLM call
@patch('agentlayer.logger.save_logs') # Patch log saving
@patch('agentlayer.logger.load_logs') # Patch log loading
async def test_langgraph_flow_violating(mock_load_logs, mock_save_logs, mock_call_llm_model, temp_agentlayer_env):
    # Mock LLM response
    mock_call_llm_model.return_value = {"prompt": "test", "result": "This output contains a forbidden word."}
    mock_load_logs.return_value = [] # Start with empty logs

    graph = langflow.build_agent_workflow()

    initial_state = {
        "input_text": "Tell me something.",
        "output_text": None,
        "role": "unallowed_role", # Will cause a role violation
        "llm_model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
        "log_id": "test-uuid-violating",
        "timestamp": datetime.utcnow().isoformat(),
        "violations": [],
        "score": 100
    }

    final_state = await graph.invoke(initial_state)

    # Assertions
    mock_call_llm_model.assert_called_once()
    assert "forbidden" in final_state["output_text"] # Check if mock output is as expected
    assert len(final_state["violations"]) == 2 # Expect keyword and role violation
    assert final_state["score"] < 100
    mock_save_logs.assert_called_once()
    saved_log = mock_save_logs.call_args[0][0][0] # Get the first log entry
    assert saved_log["uuid"] == "test-uuid-violating"
    assert len(saved_log["violations"]) == 2
    assert saved_log["score"] < 100
