# agentlayer/crew.py

import os
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Together
from typing import List, Dict, Any, Optional

# Import rule_checker for constitution validation within the crew's output
from . import rule_checker
from . import logger

# Ensure TOGETHER_API_KEY is set in environment for CrewAI to use Langchain Together LLM
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

if not TOGETHER_API_KEY:
    print("Warning: TOGETHER_API_KEY environment variable not set for CrewAI. CrewAI agents might not function.")

# Initialize the Together LLM
# CrewAI (via Langchain) will use this LLM for agent operations
# We use the explicit free model
together_llm = Together(
    model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
    together_api_key=TOGETHER_API_KEY,
    temperature=0.7,
    max_tokens=512,
    top_p=0.9
)

# Define the Agents
developer_agent = Agent(
    role='Developer',
    goal='Write precise and efficient code snippets based on user requests, ensuring best practices.',
    backstory="You are a seasoned software engineer known for your clean code and problem-solving abilities. You always consider security and compliance.",
    verbose=True,
    llm=together_llm,
    allow_delegation=False
)

analyst_agent = Agent(
    role='Analyst',
    goal='Review code and output for compliance with constitutional rules, security, and ethical guidelines.',
    backstory="You are a meticulous security and compliance analyst. Your job is to ensure that all generated content adheres to the defined constitution and ethical standards.",
    verbose=True,
    llm=together_llm,
    allow_delegation=False
)

# Define a custom task execution function to include constitution checks
def compliance_check_task_execution(code_or_output: str, request_input: str, role: str) -> Dict[str, Any]:
    """
    Performs constitution checks on the generated content.
    Returns a dictionary with compliance status and violations.
    """
    rules = rule_checker.load_constitution_rules()
    violations = rule_checker.check_violations(request_input, code_or_output, role, rules)
    
    compliance_status = "COMPLIANT" if not violations else "VIOLATED"
    score = max(0, 100 - len(violations) * 10)

    result = {
        "content": code_or_output,
        "compliance_status": compliance_status,
        "violations": violations,
        "score": score
    }
    return result


# Main function to run the crew
def run_crew(user_request: str, agent_role: str = "developer") -> Dict[str, Any]:
    """
    Runs the CrewAI multi-agent system and returns the result including constitution checks.
    """
    # Task 1: Developer writes the code/response
    developer_task = Task(
        description=f"Based on the user request '{user_request}', write a concise and safe code snippet or response. Focus on the core requirement.",
        expected_output="A clean, concise code snippet or a direct textual response.",
        agent=developer_agent
    )

    # Task 2: Analyst reviews the developer's output for compliance
    analyst_task = Task(
        description="Review the generated content for any constitution violations (e.g., forbidden keywords, role non-compliance). Provide feedback on compliance.",
        expected_output="A review indicating if the content is compliant or listing all detected violations and their severity. If compliant, state 'Compliant'. If violated, list violations.",
        agent=analyst_agent,
        context=[developer_task], # Analyst reviews Developer's output
        callback=lambda x: compliance_check_task_execution(x, user_request, agent_role) # Apply constitution check here
    )

    # Instantiate the Crew with a sequential process
    project_crew = Crew(
        agents=[developer_agent, analyst_agent],
        tasks=[developer_task, analyst_task],
        verbose=2, # Detailed logging
        process=Process.sequential # Developer -> Analyst
    )

    print(f"\n--- Running Crew for request: '{user_request}' with role: '{agent_role}' ---")
    
    try:
        # The result of the last task (analyst_task) will be returned
        # The callback ensures compliance check results are embedded in the final output
        final_result = project_crew.kickoff()
        print("\n--- Crew Execution Finished ---")
        
        # Extract the compliance check result from the analyst's task output
        # The callback returns a dict, so we need to ensure this is parsed correctly.
        # CrewAI's kickoff returns the *string output* of the last task, not the callback's raw return.
        # So we need to ensure the analyst_task output explicitly states compliance.
        # For full structured output, it's better to process the content AFTER kickoff.

        # Let's manually run the compliance check on the developer's final output for structured result
        developer_final_output_str = final_result # Assuming final_result is the developer's output string as reviewed by analyst
        
        # The analyst's output is the 'review' string, not the structured compliance dict from callback
        # We need to rerun the check on the actual generated content for structured data
        compliance_summary = compliance_check_task_execution(developer_final_output_str, user_request, agent_role)
        
        # Create a structured response
        response_data = {
            "input": user_request,
            "role": agent_role,
            "crew_output": developer_final_output_str, # The content developer produced
            "compliance_check": compliance_summary # Structured compliance details
        }
        return response_data

    except Exception as e:
        print(f"Error during crew execution: {e}")
        return {
            "input": user_request,
            "role": agent_role,
            "crew_output": f"Error: {str(e)}",
            "compliance_check": {
                "compliance_status": "ERROR",
                "violations": [],
                "score": 0
            }
        }

if __name__ == "__main__":
    # Ensure TOGETHER_API_KEY is set in environment for local testing
    os.environ["TOGETHER_API_KEY"] = os.getenv("TOGETHER_API_KEY", "YOUR_TOGETHER_API_KEY_HERE")
    if os.environ["TOGETHER_API_KEY"] == "YOUR_TOGETHER_API_KEY_HERE":
        print("Please set your TOGETHER_API_KEY environment variable to run CrewAI tests.")
    else:
        # Ensure a dummy constitution.json exists for testing
        os.makedirs("agentlayer", exist_ok=True)
        dummy_constitution_path = "agentlayer/constitution.json"
        if not os.path.exists(dummy_constitution_path):
            with open(dummy_constitution_path, "w", encoding="utf-8") as f:
                f.write("""
{
    "rules": [
        {"id": "R1", "type": "keyword", "keywords": ["delete files", "malicious"], "severity": "high"},
        {"id": "R2", "type": "role", "allowed_roles": ["developer"], "severity": "medium"}
    ]
}
                """)

        # Test case 1: Compliant request
        result1 = run_crew("Write a Python function to add two numbers.", "developer")
        print("\n--- Test Case 1 Result (Compliant) ---")
        print(json.dumps(result1, indent=2, ensure_ascii=False))

        # Test case 2: Violating request (keyword)
        result2 = run_crew("How do I maliciously delete files on a server?", "developer")
        print("\n--- Test Case 2 Result (Keyword Violation) ---")
        print(json.dumps(result2, indent=2, ensure_ascii=False))
        
        # Test case 3: Violating request (role)
        result3 = run_crew("Generate a report on financial markets.", "analyst")
        print("\n--- Test Case 3 Result (Role Violation) ---")
        print(json.dumps(result3, indent=2, ensure_ascii=False))
