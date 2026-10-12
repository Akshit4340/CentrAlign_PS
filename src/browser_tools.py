# src/browser_tools.py
import httpx
from playwright.async_api import Page, TimeoutError

class AgentTools:
    @staticmethod
    async def get_accessibility_snapshot(page: Page) -> list:
        if page.url == "about:blank":
            return []
        try:
            return await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('button, input, select, textarea')).map(el => ({
                    id: el.id || 'unassigned',
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    text: el.innerText || el.placeholder || '',
                    value: el.value || ''
                })).filter(e => e.id !== 'unassigned');
            }""")
        except Exception:
            return []

    @staticmethod
    async def execute(page: Page, action_name: str, payload: dict) -> str:
        try:
            if action_name == "navigate":
                if not payload or "url" not in payload:
                    return "Error: Missing 'url' parameter in payload."
                await page.goto(payload["url"], timeout=5000)
                return f"Successfully reached interface node: {payload['url']}"
                
            elif action_name == "type":
                element_id = payload.get('element_id') or payload.get('id')
                if not element_id:
                    return "Error: Missing 'element_id' in type payload."
                text = payload.get('text') or payload.get('value', '')
                target = f"#{element_id}"
                await page.wait_for_selector(target, timeout=3000)
                await page.fill(target, str(text))
                return f"Populated input entry field: {element_id}"
                
            elif action_name == "click":
                element_id = payload.get('element_id') or payload.get('id')
                if not element_id:
                    return "Error: Missing 'element_id' in click payload."
                target = f"#{element_id}"
                await page.wait_for_selector(target, timeout=3000)
                await page.click(target)
                return f"Executed click on target structural node: {element_id}"
                
            elif action_name == "verify_outcome":
                # Fallback guard matching syllabus rule 6 to catch missing keys gracefully
                target_vendor = payload.get("vendor", "Company X")
                
                async with httpx.AsyncClient() as client:
                    # Explicit local resolution binding to prevent getaddrinfo issues
                    res = await client.get("http://127.0.0.1:8000/api/invoices", timeout=5.0)
                    if res.status_code != 200:
                        return f"VERIFICATION_FAILURE: Backend database API returned status {res.status_code}"
                    records = res.json()
                
                for record in records:
                    if target_vendor.lower() in str(record.get("vendor", "")).lower():
                        return f"VERIFICATION_SUCCESS: Record for {target_vendor} verified inside backend storage."
                return f"VERIFICATION_FAILURE: Vendor '{target_vendor}' missing from transaction ledger rows."
                
        except TimeoutError:
            return f"Timeout Error: Target interaction element node '#{payload.get('element_id', 'unknown')}' was missing."
        except Exception as e:
            return f"System Execution Exception Error: {str(e)}"
