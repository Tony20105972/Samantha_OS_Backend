# agentlayer/llm_agent.py

import os
import httpx
from typing import TypedDict, Optional, Dict, Any

class AgentState(TypedDict):
    prompt: str
    result: Optional[str]

# TOGETHER_API_KEY는 Render 환경 변수에서 가져옴
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TOGETHER_API_BASE = "https://api.together.xyz/v1/chat/completions"

client = httpx.AsyncClient()

async def call_llm_model(state: AgentState, model_name: str) -> AgentState:
    """
    Together AI의 LLM을 호출하여 프롬프트에 대한 응답을 생성합니다.
    사용자가 지정한 llm_model을 사용합니다.
    """
    prompt = state["prompt"]
    if not prompt:
        return {**state, "result": "❌ No prompt provided to LLM."}

    if not TOGETHER_API_KEY:
        return {**state, "result": "❌ TOGETHER_API_KEY environment variable not set."}

    try:
        messages = [
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOGETHER_API_KEY}"
        }

        response = await client.post(TOGETHER_API_BASE, json=payload, headers=headers, timeout=60.0)
        response.raise_for_status()

        response_data = response.json()
        
        if response_data and response_data.get("choices"):
            generated_text = response_data["choices"][0]["message"]["content"]
            return {**state, "result": generated_text.strip()}
        else:
            return {**state, "result": f"❌ LLM API did not return valid choices: {response_data}"}

    except httpx.RequestError as e:
        return {**state, "result": f"❌ Network error contacting Together AI: {str(e)}"}
    except httpx.HTTPStatusError as e:
        return {**state, "result": f"❌ Together AI API returned an error: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {**state, "result": f"❌ Unexpected error during LLM generation: {str(e)}"}

if __name__ == "__main__":
    import asyncio

    async def test_call_llm_model_main():
        # 테스트를 위해 임시로 환경 변수 설정
        # 실제 배포 시에는 Render 대시보드에서 설정합니다.
        os.environ["TOGETHER_API_KEY"] = os.getenv("TOGETHER_API_KEY", "YOUR_TOGETHER_API_KEY_HERE")

        print("Testing llm_agent.py with Together AI (dynamic model selection)...")
        if not TOGETHER_API_KEY or TOGETHER_API_KEY == "YOUR_TOGETHER_API_KEY_HERE":
            print("Please set your TOGETHER_API_KEY environment variable to run tests.")
            return

        models_to_test = [
            "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free", # 무료 모델
            "microsoft/phi-3-mini-4k-instruct", # Together AI에서 지원하는 다른 인기 모델
            # "mistralai/Mistral-7B-Instruct-v0.2", # 테스트용으로 다른 모델 추가 가능
        ]

        for model_to_use in models_to_test:
            print(f"\n--- Testing with model: {model_to_use} ---")
            test_prompt = f"Explain the concept of AI agent layers in simple terms, focusing on constitution guard. (using {model_to_use})"
            initial_state: AgentState = {"prompt": test_prompt, "result": None}
            final_state = await call_llm_model(initial_state, model_to_use)
            print(f"Prompt: {test_prompt}")
            print(f"Result: {final_state['result']}")
            
            if "❌" in final_state['result']:
                print(f"Test for {model_to_use} FAILED.")
            else:
                print(f"Test for {model_to_use} PASSED.")
        
        await client.aclose() # 클라이언트 종료

    asyncio.run(test_call_llm_model_main())
