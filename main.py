# main.py
import os
import sys
import asyncio
import subprocess
import time
import httpx
from dotenv import load_dotenv
from src.llm_client import OllamaClient
from src.agent_loop import AutonomousAgentEngine

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
TARGET_APP_URL = os.getenv("TARGET_APP_URL", "http://127.0.0.1:8000")
MAX_STEP_CAP = int(os.getenv("MAX_STEP_CAP", "10"))

async def verify_local_service(url: str) -> bool:
    for _ in range(5):
        try:
            async with httpx.AsyncClient() as client:
                if (await client.get(url)).status_code == 200:
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False

async def check_ollama(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(base_url, timeout=5.0)
            return res.status_code == 200
    except Exception:
        return False

async def main():
    ollama_ready = await check_ollama(OLLAMA_BASE_URL)
    if not ollama_ready:
        print(f"[*] Notice: Local Ollama instance not detected at {OLLAMA_BASE_URL}.")
        print("[*] UnifiedLLMClient will use Cloud LLM or autonomous DOM-semantic reasoning mode.")

    app_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    if not await verify_local_service(TARGET_APP_URL):
        print("[!] Target testing application server failed to initialize correctly.")
        app_process.terminate()
        return

    try:
        ollama_client = OllamaClient(model_name=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
        agent = AutonomousAgentEngine(llm_client=ollama_client)
        
        goal_task = (
            f"Navigate to {TARGET_APP_URL}, enter Company X into v_name, input 450.75 into v_amt, "
            "set v_date to 2026-11-15, execute submit_invoice_btn, and verify the record is saved correctly."
        )
        await agent.run_task(goal=goal_task, max_steps=MAX_STEP_CAP)
    finally:
        app_process.terminate()
        print("[*] Local evaluation ecosystem tear-down completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())

