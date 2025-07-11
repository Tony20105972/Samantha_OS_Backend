# agentlayer/logger.py

import json
import os
from typing import List, Dict, Any

def load_logs() -> List[Dict[str, Any]]:
    """
    Loads execution logs from log.json.
    """
    log_path = "agentlayer/log.json"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {log_path}. Returning empty list.")
                return [] # Handle empty or corrupted JSON
    return []

def save_logs(logs: List[Dict[str, Any]]):
    """
    Saves execution logs to log.json.
    """
    log_path = "agentlayer/log.json"
    os.makedirs(os.path.dirname(log_path), exist_ok=True) # Ensure directory exists
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False) # ensure_ascii=False for Korean characters

if __name__ == "__main__":
    # Ensure a dummy log.json exists for testing
    os.makedirs("agentlayer", exist_ok=True)
    dummy_log_path = "agentlayer/log.json"
    if not os.path.exists(dummy_log_path):
        with open(dummy_log_path, "w", encoding="utf-8") as f:
            f.write("[]")

    print("--- Testing logger.py ---")

    # Test loading empty logs
    loaded_empty_logs = load_logs()
    print(f"Loaded empty logs: {loaded_empty_logs}") # Expected: []

    # Test saving new logs
    new_log_entry = {
        "uuid": "test-uuid-1",
        "timestamp": "2025-07-11T10:00:00Z",
        "input": "test input",
        "output": "test output",
        "role": "developer",
        "violations": [],
        "score": 100
    }
    logs_to_save = [new_log_entry]
    save_logs(logs_to_save)
    print(f"Saved log: {new_log_entry['uuid']}")

    # Test loading saved logs
    loaded_logs_after_save = load_logs()
    print(f"Loaded logs after save: {loaded_logs_after_save}") # Expected: [new_log_entry]

    # Test appending to existing logs
    another_log_entry = {
        "uuid": "test-uuid-2",
        "timestamp": "2025-07-11T10:05:00Z",
        "input": "another test input",
        "output": "another test output",
        "role": "analyst",
        "violations": [{"rule_id": "R1", "type": "keyword", "trigger": "test", "severity": "low"}],
        "score": 90
    }
    existing_logs = load_logs()
    existing_logs.append(another_log_entry)
    save_logs(existing_logs)
    print(f"Appended log: {another_log_entry['uuid']}")

    final_logs = load_logs()
    print(f"Final logs: {final_logs}") # Expected: [new_log_entry, another_log_entry]
