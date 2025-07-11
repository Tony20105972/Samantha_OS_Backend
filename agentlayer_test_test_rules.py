# agentlayer/test/test_rules.py

import pytest
import os
import json
from .. import rule_checker # Import from parent directory

# Define a fixture for a temporary constitution.json
@pytest.fixture
def temp_constitution_file(tmp_path):
    # Ensure agentlayer directory exists for test
    test_dir = tmp_path / "agentlayer"
    test_dir.mkdir()
    constitution_path = test_dir / "constitution.json"
    
    sample_rules_content = {
        "rules": [
            {"id": "R1", "type": "keyword", "keywords": ["secret", "confidential"], "severity": "high"},
            {"id": "R2", "type": "role", "allowed_roles": ["admin", "developer"], "severity": "medium"},
            {"id": "R3", "type": "keyword", "keywords": ["badword"], "severity": "low"}
        ]
    }
    with open(constitution_path, "w", encoding="utf-8") as f:
        json.dump(sample_rules_content, f)
    
    # Temporarily change the current working directory to allow rule_checker to find the file
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield constitution_path
    os.chdir(original_cwd) # Change back after test

def test_load_constitution_rules(temp_constitution_file):
    rules = rule_checker.load_constitution_rules()
    assert len(rules) == 3
    assert any(r["id"] == "R1" for r in rules)
    assert any(r["id"] == "R2" for r in rules)
    assert any(r["id"] == "R3" for r in rules)

def test_load_constitution_rules_no_file(tmp_path):
    # Ensure no constitution.json exists
    test_dir = tmp_path / "agentlayer"
    test_dir.mkdir()
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    rules = rule_checker.load_constitution_rules()
    assert rules == []
    os.chdir(original_cwd)

def test_check_violations_no_violations(temp_constitution_file):
    rules = rule_checker.load_constitution_rules()
    input_text = "This is a normal query."
    output_text = "Here is the response."
    role = "developer"
    violations = rule_checker.check_violations(input_text, output_text, role, rules)
    assert violations == []

def test_check_violations_keyword_in_input(temp_constitution_file):
    rules = rule_checker.load_constitution_rules()
    input_text = "Access the secret database."
    output_text = "Accessing data."
    role = "developer"
    violations = rule_checker.check_violations(input_text, output_text, role, rules)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "R1"
    assert violations[0]["type"] == "keyword"
    assert violations[0]["trigger"] == "secret"

def test_check_violations_keyword_in_output(temp_constitution_file):
    rules = rule_checker.load_constitution_rules()
    input_text = "Generate some text."
    output_text = "Here is some confidential information."
    role = "developer"
    violations = rule_checker.check_violations(input_text, output_text, role, rules)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "R1"
    assert violations[0]["type"] == "keyword"
    assert violations[0]["trigger"] == "confidential"

def test_check_violations_role_not_allowed(temp_constitution_file):
    rules = rule_checker.load_constitution_rules()
    input_text = "Perform some analysis."
    output_text = "Analysis complete."
    role = "user" # Not in allowed_roles for R2
    violations = rule_checker.check_violations(input_text, output_text, role, rules)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "R2"
    assert violations[0]["type"] == "role"
    assert violations[0]["trigger"] == "user"

def test_check_violations_multiple_violations(temp_constitution_file):
    rules = rule_checker.load_constitution_rules()
    input_text = "This contains a badword and secret info."
    output_text = "Also a badword here."
    role = "guest"
    violations = rule_checker.check_violations(input_text, output_text, role, rules)
    assert len(violations) == 3 # R1 (secret), R3 (badword), R2 (role)
    violation_ids = sorted([v["rule_id"] for v in violations])
    assert violation_ids == ["R1", "R2", "R3"]

def test_check_violations_case_insensitivity(temp_constitution_file):
    rules = rule_checker.load_constitution_rules()
    input_text = "This is a SECRET."
    output_text = "No CONFIDENTIAL data."
    role = "DeVeLoPeR"
    violations = rule_checker.check_violations(input_text, output_text, role, rules)
    assert len(violations) == 2 # R1 (secret), R1 (confidential)
    assert all(v["rule_id"] == "R1" for v in violations)
