# src/agent_loop.py
import json
import asyncio
import base64
import os
from typing import Optional, Callable, Awaitable
from pydantic import BaseModel, Field
from config.prompt import AGENT_SYSTEM_PROMPT
from src.browser_tools import AgentTools

class TaskState(BaseModel):
    goal: str
    facts_found: dict = Field(default_factory=dict)
    steps_completed: list = Field(default_factory=list)
    errors_encountered: list = Field(default_factory=list)

class AutonomousAgentEngine:
    def __init__(
        self,
        llm_client,
        on_event: Optional[Callable[[str, dict], Awaitable[None]]] = None,
        hitl_handler: Optional[Callable[[str, dict], Awaitable[bool]]] = None,
        headless: bool = False
    ):
        self.llm = llm_client
        self.state = None
        self.last_action_signature = None
        self.on_event = on_event
        self.hitl_handler = hitl_handler
        self.headless = headless

    async def _emit(self, event_type: str, data: dict):
        if self.on_event:
            try:
                await self.on_event(event_type, data)
            except Exception as e:
                print(f"[!] Event emission error ({event_type}): {e}")

    async def execute_with_backoff(self, page, name, payload, retries=3):
        delay = 1.0
        last_error = ""
        for attempt in range(retries):
            observation = await AgentTools.execute(page, name, payload)
            if "Timeout Error" in observation:
                last_error = f"Transient Timeout on attempt {attempt+1}"
                await asyncio.sleep(delay)
                delay *= 2
            elif "Exception Error" in observation:
                self.state.errors_encountered.append(f"Fatal Selection Anomaly: {observation}")
                return f"Bad Selector Block: {observation}"
            else:
                return observation
        return f"Failed after maximum threshold limits. Error: {last_error}"

    async def run_task(self, goal: str, max_steps: int = 10) -> bool:
        from playwright.async_api import async_playwright
        self.state = TaskState(goal=goal)
        success = False
        
        await self._emit("TASK_STARTED", {"goal": goal, "max_steps": max_steps})

        async with async_playwright() as p:
            # Respect environment or parameter for headless
            browser_headless = self.headless or os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
            browser = await p.chromium.launch(headless=browser_headless)
            page = await browser.new_page()
            
            for step in range(1, max_steps + 1):
                snapshots = await AgentTools.get_accessibility_snapshot(page)
                
                await self._emit("STEP_START", {
                    "step": step,
                    "url": page.url,
                    "interactive_dom": snapshots
                })

                prompt = (
                    f"{AGENT_SYSTEM_PROMPT}\n\nTask Goal: {self.state.goal}\n"
                    f"Current URL: {page.url}\n"
                    f"Facts Discovered: {json.dumps(self.state.facts_found)}\n"
                    f"Steps History: {json.dumps(self.state.steps_completed)}\n"
                    f"Interactive DOM Map: {json.dumps(snapshots)}\nOutput JSON String:"
                )
                
                try:
                    raw_response = self.llm.generate_decision(prompt)
                    decision = json.loads(raw_response)
                except Exception as e:
                    print(f"[*] Parsing structure break step {step}: {str(e)}")
                    err_msg = f"Step {step}: JSON parse error - {str(e)}"
                    self.state.errors_encountered.append(err_msg)
                    await self._emit("STEP_ERROR", {"step": step, "error": err_msg})
                    break
                
                thought = decision.get("thought", "")
                action = decision.get("action", {})
                name = action.get("name", "")
                payload = action.get("payload", {})
                
                print(f"\n[Step {step}] Thought: {thought}")
                print(f"Action Selection: {name}({json.dumps(payload)})")

                await self._emit("STEP_DECISION", {
                    "step": step,
                    "thought": thought,
                    "action": name,
                    "payload": payload
                })
                
                action_signature = f"{name}-{json.dumps(payload)}"
                if action_signature == self.last_action_signature:
                    print("[!] Consecutive duplicate action detected. Skipping to avoid infinite loop.")
                    await self._emit("STEP_SKIPPED", {"step": step, "reason": "Duplicate consecutive action"})
                    continue
                self.last_action_signature = action_signature

                # Human-In-The-Loop Privilege Gate
                # Triggers on any click/type action involving commit-like operations
                sensitive_keywords = ["submit", "save", "commit", "confirm", "delete", "approve", "send"]
                payload_text = str(payload.values()).lower()
                is_sensitive = name == "click" and any(kw in payload_text for kw in sensitive_keywords)
                if is_sensitive:
                    print(f"\n[!! HITL PRIVILEGE GATE]: Confirm commit state layout operation? {payload}")
                    approved = False
                    
                    if self.hitl_handler:
                        await self._emit("HITL_REQUIRED", {
                            "step": step,
                            "action": name,
                            "payload": payload,
                            "message": f"Autonomous agent requests permission to commit transaction for {payload}."
                        })
                        approved = await self.hitl_handler(name, payload)
                    else:
                        loop = asyncio.get_event_loop()
                        approval_input = await loop.run_in_executor(None, input, "Type 'approve' to proceed: ")
                        approved = (approval_input.strip().lower() == "approve")

                    await self._emit("HITL_RESOLVED", {"approved": approved})

                    if not approved:
                        print("[*] Operation execution refused by human controller.")
                        self.state.errors_encountered.append("Execution aborted by human controller during HITL gate.")
                        await self._emit("STEP_ERROR", {"step": step, "error": "Aborted by human reviewer"})
                        break

                # Execute action
                observation = await self.execute_with_backoff(page, name, payload)
                print(f"Observation Feedback: {observation}")

                # Capture browser screenshot for UI monitoring
                try:
                    screenshot_bytes = await page.screenshot(type="jpeg", quality=65)
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                except Exception:
                    screenshot_b64 = None

                step_record = f"Step {step}: {name}({json.dumps(payload)}) -> {observation}"
                self.state.steps_completed.append(step_record)

                await self._emit("STEP_OBSERVATION", {
                    "step": step,
                    "action": name,
                    "payload": payload,
                    "observation": observation,
                    "screenshot": screenshot_b64
                })
                
                if "VERIFICATION_SUCCESS" in observation:
                    print("\n" + "="*70 + "\n[Task Success] Target metrics confirmed.")
                    success = True
                    break
                    
                await asyncio.sleep(1)
                
            await browser.close()

        summary = self.get_summary()
        await self._emit("TASK_FINISHED", {
            "success": success,
            "summary": summary,
            "steps_count": len(self.state.steps_completed),
            "errors": self.state.errors_encountered
        })
        return success

    def get_summary(self) -> str:
        if not self.state:
            return "No task has been executed yet."
        
        lines = []
        lines.append("=" * 70)
        lines.append("  TASK EXECUTION SUMMARY REPORT")
        lines.append("=" * 70)
        lines.append(f"\n  Goal: {self.state.goal}\n")
        
        lines.append("-" * 70)
        lines.append("  STEPS COMPLETED:")
        lines.append("-" * 70)
        if self.state.steps_completed:
            for step_entry in self.state.steps_completed:
                lines.append(f"    {step_entry}")
        else:
            lines.append("    (No steps were completed)")
        
        if self.state.errors_encountered:
            lines.append(f"\n{'-' * 70}")
            lines.append("  ERRORS ENCOUNTERED:")
            lines.append("-" * 70)
            for error in self.state.errors_encountered:
                lines.append(f"    [!] {error}")
        
        lines.append(f"\n{'=' * 70}")
        has_success = any("VERIFICATION_SUCCESS" in s for s in self.state.steps_completed)
        if has_success:
            lines.append("  RESULT: SUCCESS - Task completed and verified.")
        else:
            lines.append("  RESULT: INCOMPLETE - Task did not reach verification.")
        lines.append("=" * 70)
        
        return "\n".join(lines)
