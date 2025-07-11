# agentlayer/cli.py

import click
import os
import json
import requests
import asyncio
from datetime import datetime
import yaml

# Base URL for the FastAPI service (for CLI to interact with)
# For local testing: http://127.0.0.1:8000
# For Render deployment: your_render_service_url
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# --- Utility Functions (Local) ---
# These are kept minimal as main logic is in FastAPI and other modules
def _init_project_scaffold():
    """Initializes the agentlayer project structure."""
    base_dir = "agentlayer"
    os.makedirs(base_dir, exist_ok=True)

    files_to_create = {
        "cli.py": "# CLI entry point\n",
        "config.yaml": "default_agent: myagent\n",
        "constitution.json": """
{
    "rules": [
        {"id": "R1", "type": "keyword", "keywords": ["sudo", "rm -rf"], "severity": "high"},
        {"id": "R2", "type": "role", "allowed_roles": ["developer", "analyst"], "severity": "medium"}
    ]
}
""",
        "llm_agent.py": "# LLM agent logic\n",
        "logger.py": "# Logging utility\n",
        "langflow.py": "# LangGraph flow\n",
        "crew.py": "# CrewAI setup\n",
        "api.py": "# FastAPI app\n",
        "rule_checker.py": "# Constitution rule checker\n",
        "log.json": "[]"
    }

    for filename, content in files_to_create.items():
        filepath = os.path.join(base_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")
            click.echo(f"  Created: {filepath}")
    
    # Create test directory
    os.makedirs(os.path.join(base_dir, "test"), exist_ok=True)
    test_files_to_create = {
        "test/test_rules.py": "# Pytest for rules\n",
        "test/test_flow.py": "# Pytest for flow\n"
    }
    for filename, content in test_files_to_create.items():
        filepath = os.path.join(base_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")
            click.echo(f"  Created: {filepath}")

    click.echo("✅ AgentLayer project scaffold initialized.")


# --- CLI Commands ---
@click.group()
def cli():
    """AgentLayer CLI for managing AI agents and their constitution."""
    pass

@cli.command()
def init():
    """
    Initializes the basic AgentLayer project structure.
    """
    click.echo("Initializing AgentLayer project scaffold...")
    _init_project_scaffold()
    click.echo("Please review the generated files and set your TOGETHER_API_KEY environment variable.")

@cli.command()
@click.argument('input_text')
@click.option('--role', default='developer', help='Role of the agent (e.g., developer, analyst).')
@click.option('--model', default='deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free', help='LLM model to use for the agent.')
def run(input_text: str, role: str, model: str):
    """
    Runs an AI agent with the given input and records the result.
    """
    click.echo(f"Running agent with input: '{input_text}' (Role: {role}, Model: {model})...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/run",
            json={"input_text": input_text, "role": role, "llm_model": model},
            timeout=120 # Increased timeout for LLM calls
        )
        response.raise_for_status()
        result = response.json()
        
        click.echo("\n--- Agent Execution Result ---")
        click.echo(f"UUID: {result['uuid']}")
        click.echo(f"Timestamp: {result['timestamp']}")
        click.echo(f"Input: {result['input']}")
        click.echo(f"Output: {result['output']}")
        click.echo(f"Role: {result['role']}")
        click.echo(f"LLM Model: {result['llm_model']}")
        if result['violations']:
            click.echo("Violations Detected:")
            for violation in result['violations']:
                click.echo(f"  - Rule ID: {violation['rule_id']}, Type: {violation['type']}, Trigger: '{violation['trigger']}', Severity: {violation['severity']}")
            click.echo(f"Score: {result['score']} / 100 ❌")
        else:
            click.echo("Violations: None ✅")
            click.echo(f"Score: {result['score']} / 100 ✅")

    except requests.exceptions.RequestException as e:
        click.echo(f"❌ Error communicating with the API: {e}")
        if e.response is not None:
            click.echo(f"API Response: {e.response.text}")
    except json.JSONDecodeError:
        click.echo("❌ Error: Could not decode JSON response from API.")
    except Exception as e:
        click.echo(f"❌ An unexpected error occurred: {e}")

@cli.command('constitution-validate')
def constitution_validate():
    """
    Validates the constitution.json file.
    """
    click.echo("Validating constitution.json...")
    try:
        constitution_path = "agentlayer/constitution.json"
        if not os.path.exists(constitution_path):
            click.echo(f"❌ Error: {constitution_path} not found. Run 'agentlayer init' first.")
            return

        with open(constitution_path, "r", encoding="utf-8") as f:
            rules = json.load(f).get("rules", [])
        
        click.echo("\n--- Constitution Rules ---")
        if not rules:
            click.echo("No rules defined in constitution.json. (Consider adding rules for effective governance.)")
        else:
            click.echo(json.dumps(rules, indent=2, ensure_ascii=False))
        
        # Basic structural validation
        for i, rule in enumerate(rules):
            if "id" not in rule or "type" not in rule or "severity" not in rule:
                click.echo(f"⚠️ Warning: Rule {i+1} is missing required fields (id, type, severity).")
            if rule.get("type") == "keyword" and "keywords" not in rule:
                click.echo(f"⚠️ Warning: Keyword rule {rule.get('id')} is missing 'keywords' field.")
            if rule.get("type") == "role" and "allowed_roles" not in rule:
                click.echo(f"⚠️ Warning: Role rule {rule.get('id')} is missing 'allowed_roles' field.")
        
        click.echo("\n✅ Constitution validation checks complete.")

    except json.JSONDecodeError:
        click.echo("❌ Error: constitution.json is not a valid JSON file.")
    except Exception as e:
        click.echo(f"❌ An unexpected error occurred during validation: {e}")


@cli.command('agent-add')
@click.argument('agent_name')
def agent_add(agent_name: str):
    """
    Adds a new agent scaffold to the project.
    """
    agent_path = os.path.join("agentlayer", f"{agent_name}.agent.py")
    if os.path.exists(agent_path):
        click.echo(f"⚠️ Agent '{agent_name}' already exists at {agent_path}.")
        return

    with open(agent_path, "w", encoding="utf-8") as f:
        f.write(f"# Agent: {agent_name}\n")
        f.write("# Add your agent-specific logic here (e.g., LangGraph nodes, CrewAI tasks)\n")
    click.echo(f"✅ Agent '{agent_name}' scaffold created at {agent_path}.")

    config_path = "agentlayer/config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if not config:
                config = {}
        config['agents'] = config.get('agents', [])
        if agent_name not in config['agents']:
            config['agents'].append(agent_name)
        
        # Set this new agent as default if no default is set
        if 'default_agent' not in config:
            config['default_agent'] = agent_name

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, indent=2, allow_unicode=True)
        click.echo(f"Updated {config_path} with agent '{agent_name}'.")
    except FileNotFoundError:
        click.echo(f"❌ Warning: {config_path} not found. Creating a new one.")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump({"default_agent": agent_name, "agents": [agent_name]}, f, indent=2, allow_unicode=True)
    except Exception as e:
        click.echo(f"❌ Error updating {config_path}: {e}")


@cli.command()
@click.argument('trace_uuid')
def trace(trace_uuid: str):
    """
    Traces a specific agent execution by UUID.
    """
    click.echo(f"Tracing execution with UUID: {trace_uuid}...")
    try:
        response = requests.get(f"{API_BASE_URL}/trace/{trace_uuid}", timeout=30)
        response.raise_for_status()
        result = response.json()
        
        click.echo("\n--- Execution Trace ---")
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            click.echo(f"❌ Error: No log found for UUID '{trace_uuid}'.")
        else:
            click.echo(f"❌ API Error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        click.echo(f"❌ Network error: {e}")
    except Exception as e:
        click.echo(f"❌ An unexpected error occurred: {e}")

@cli.command()
def score():
    """
    Gets the overall constitution compliance score.
    """
    click.echo("Calculating overall constitution score...")
    try:
        response = requests.get(f"{API_BASE_URL}/score", timeout=30)
        response.raise_for_status()
        result = response.json()

        click.echo("\n--- Overall Constitution Score ---")
        click.echo(f"Total Runs: {result['total_runs']}")
        click.echo(f"Average Score: {result['average_score']} / 100")
        if result['violation_summary']:
            click.echo("Violation Summary (Rule ID: Count):")
            for rule_id, count in result['violation_summary'].items():
                click.echo(f"  - {rule_id}: {count} times")
        else:
            click.echo("No violations recorded across all runs. ✅")

    except requests.exceptions.RequestException as e:
        click.echo(f"❌ Error communicating with the API: {e}")
        if e.response is not None:
            click.echo(f"API Response: {e.response.text}")
    except Exception as e:
        click.echo(f"❌ An unexpected error occurred: {e}")

@cli.command()
def report():
    """
    Generates an HTML report of all agent executions.
    """
    click.echo("Generating HTML report...")
    try:
        response = requests.get(f"{API_BASE_URL}/report", timeout=60)
        response.raise_for_status()
        
        report_html_path = "agentlayer_report.html"
        with open(report_html_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        click.echo(f"✅ HTML report generated at: {os.path.abspath(report_html_path)}")
        click.echo("You can open this file in your web browser to view the report.")

    except requests.exceptions.RequestException as e:
        click.echo(f"❌ Error communicating with the API: {e}")
        if e.response is not None:
            click.echo(f"API Response: {e.response.text}")
    except Exception as e:
        click.echo(f"❌ An unexpected error occurred: {e}")

if __name__ == '__main__':
    cli()
