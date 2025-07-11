# agentlayer/rule_checker.py

import json
import os
from typing import Dict, Any, List

def load_constitution_rules() -> List[Dict[str, Any]]:
    """
    Loads constitution rules from constitution.json.
    """
    constitution_path = "agentlayer/constitution.json"
    if os.path.exists(constitution_path):
        with open(constitution_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data.get("rules", [])
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {constitution_path}. Returning empty rules.")
                return []
    return []

def check_violations(input_text: str, output_text: str, role: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Checks the input, output, and role against the constitution rules for violations.
    """
    violations = []

    for rule in rules:
        rule_id = rule.get("id", "unknown")
        rule_type = rule.get("type")
        severity = rule.get("severity", "low")

        if rule_type == "keyword":
            for keyword in rule.get("keywords", []):
                # Case-insensitive check
                if keyword.lower() in input_text.lower() or (output_text and keyword.lower() in output_text.lower()):
                    violations.append({
                        "rule_id": rule_id,
                        "type": "keyword",
                        "trigger": keyword,
                        "severity": severity
                    })
        elif rule_type == "role":
            allowed_roles = rule.get("allowed_roles", [])
            if role not in allowed_roles:
                violations.append({
                    "rule_id": rule_id,
                    "type": "role",
                    "trigger": role,
                    "severity": severity
                })
        # Add other rule types here if needed (e.g., "length", "format")
    return violations

if __name__ == "__main__":
    # Ensure a dummy constitution.json exists for testing
    os.makedirs("agentlayer", exist_ok=True)
    dummy_constitution_path = "agentlayer/constitution.json"
    if not os.path.exists(dummy_constitution_path):
        with open(dummy_constitution_path, "w", encoding="utf-8") as f:
            f.write("""
{
    "rules": [
        {"id": "R1", "type": "keyword", "keywords": ["sudo", "rm -rf"], "severity": "high"},
        {"id": "R2", "type": "role", "allowed_roles": ["developer", "architect"], "severity": "medium"},
        {"id": "R3", "type": "keyword", "keywords": ["unethical"], "severity": "critical"}
    ]
}
            """)

    print("--- Testing rule_checker.py ---")

    rules = load_constitution_rules()
    print(f"Loaded Rules: {json.dumps(rules, indent=2)}")

    # Test case 1: No violations
    input1 = "Please write a simple Python function."
    output1 = "```python\ndef hello(): return 'Hello'\n```"
    role1 = "developer"
    v1 = check_violations(input1, output1, role1, rules)
    print(f"\nTest 1 (No violations): Input='{input1}', Output='{output1}', Role='{role1}'")
    print(f"Violations: {v1}") # Expected: []

    # Test case 2: Keyword violation in input
    input2 = "I need to run sudo commands."
    output2 = "Acknowledged."
    role2 = "developer"
    v2 = check_violations(input2, output2, role2, rules)
    print(f"\nTest 2 (Keyword violation in input): Input='{input2}', Output='{output2}', Role='{role2}'")
    print(f"Violations: {v2}") # Expected: [{"rule_id": "R1", "type": "keyword", "trigger": "sudo", "severity": "high"}]

    # Test case 3: Role violation
    input3 = "Analyze the market trends."
    output3 = "Analysis complete."
    role3 = "analyst" # Not in allowed_roles for R2 (developer, architect)
    v3 = check_violations(input3, output3, role3, rules)
    print(f"\nTest 3 (Role violation): Input='{input3}', Output='{output3}', Role='{role3}'")
    print(f"Violations: {v3}") # Expected: [{"rule_id": "R2", "type": "role", "trigger": "analyst", "severity": "medium"}]

    # Test case 4: Multiple violations (keyword in output, and role)
    input4 = "Write a script to delete files."
    output4 = "To rm -rf files, use this script..." # Forbidden keyword in output
    role4 = "tester" # Not allowed
    v4 = check_violations(input4, output4, role4, rules)
    print(f"\nTest 4 (Multiple violations): Input='{input4}', Output='{output4}', Role='{role4}'")
    print(f"Violations: {v4}") # Expected: two violations, one for keyword, one for role
