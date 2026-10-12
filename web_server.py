# web_server.py
import os
import sys
import json
import asyncio
import uuid
import shutil
import subprocess
from typing import Dict, Any, Optional
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.advanced_rag import AdvancedRAGEngine
from src.llm_client import UnifiedLLMClient
from src.agent_loop import AutonomousAgentEngine

app = FastAPI(title="CentrAlign AI Autonomous Task Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
SAMPLES_DIR = "samples"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)

# Shared RAG engine & LLM Client
rag_engine = AdvancedRAGEngine()
llm_client = UnifiedLLMClient()

# Active agent execution sessions and HITL futures
active_sessions: Dict[str, Dict[str, Any]] = {}

class QueryRequest(BaseModel):
    query: str

class AgentRunRequest(BaseModel):
    goal: Optional[str] = None
    use_extracted_invoice: bool = True
    max_steps: int = 10
    auto_approve: bool = False

class HitlDecision(BaseModel):
    session_id: str
    approved: bool

# ----------------------------------------------------------------
# Internal Service Check & Auto-start Ledger Server
# ----------------------------------------------------------------
ledger_process: Optional[subprocess.Popen] = None

async def ensure_ledger_running():
    global ledger_process
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("http://127.0.0.1:8000/api/invoices", timeout=1.5)
            if r.status_code == 200:
                return True
        except Exception:
            pass

    # Start ledger in background if not already running
    try:
        ledger_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        await asyncio.sleep(1.5)
        return True
    except Exception as e:
        print(f"[!] Could not auto-start ledger server: {e}")
        return False

# ----------------------------------------------------------------
# File Upload & Sample Loader Endpoints
# ----------------------------------------------------------------
@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename or f"doc_{uuid.uuid4().hex[:6]}.pdf"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Reset RAG knowledge store before loading new document to avoid chunk accumulation
    rag_engine.reset()

    ext = filename.lower().split(".")[-1]
    chunks = []
    
    if ext == "pdf":
        chunks = rag_engine.ingest_pdf_file(filepath)
    elif ext in ["png", "jpg", "jpeg", "webp"]:
        chunks = rag_engine.ingest_image_file(filepath)
    else:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        chunks = rag_engine.ingest_text(content, source_name=filename)

    entities = rag_engine.extract_invoice_entities()

    return {
        "status": "success",
        "filename": filename,
        "extension": ext,
        "chunks_indexed": len(chunks),
        "total_knowledge_chunks": len(rag_engine.chunks),
        "entities": entities.model_dump()
    }

@app.post("/api/load-sample")
async def load_sample(sample_type: str = Form(...)):
    mapping = {
        "company_x_pdf": ("invoice_company_x.pdf", "pdf"),
        "acme_pdf": ("invoice_acme_corp.pdf", "pdf"),
        "company_x_img": ("invoice_company_x.png", "image"),
        "apex_img": ("invoice_apex_tech.png", "image")
    }
    
    if sample_type not in mapping:
        raise HTTPException(status_code=400, detail="Invalid sample type")

    # Reset RAG engine to prevent chunk accumulation across loads
    rag_engine.reset()

    filename, kind = mapping[sample_type]
    filepath = os.path.join(SAMPLES_DIR, filename)

    if not os.path.exists(filepath):
        from src.create_samples import generate_pdf_invoice, generate_image_invoice
        if filename == "invoice_company_x.pdf":
            generate_pdf_invoice(filepath, "Company X", 450.75, "2026-11-15", "INV-2026-001")
        elif filename == "invoice_acme_corp.pdf":
            generate_pdf_invoice(filepath, "Acme Corp", 895.00, "2026-12-05", "INV-2026-088")
        elif filename == "invoice_company_x.png":
            generate_image_invoice(filepath, "Company X", 450.75, "2026-11-15", "INV-2026-001")
        elif filename == "invoice_apex_tech.png":
            generate_image_invoice(filepath, "Apex Global", 1280.00, "2026-11-30", "INV-2026-554")

    if kind == "pdf":
        chunks = rag_engine.ingest_pdf_file(filepath)
    else:
        chunks = rag_engine.ingest_image_file(filepath)

    entities = rag_engine.extract_invoice_entities()

    return {
        "status": "success",
        "sample_type": sample_type,
        "filename": filename,
        "chunks_indexed": len(chunks),
        "total_knowledge_chunks": len(rag_engine.chunks),
        "entities": entities.model_dump()
    }

# ----------------------------------------------------------------
# Advanced RAG Query Endpoint
# ----------------------------------------------------------------
@app.post("/api/rag/query")
async def query_rag(req: QueryRequest):
    result = rag_engine.generate_grounded_answer(req.query)
    return result

# ----------------------------------------------------------------
# Autonomous Agent Execution with Streaming Events & HITL
# ----------------------------------------------------------------
@app.post("/api/agent/run")
async def start_agent_task(req: AgentRunRequest):
    await ensure_ledger_running()

    session_id = str(uuid.uuid4())
    event_queue: asyncio.Queue = asyncio.Queue()
    hitl_future: Optional[asyncio.Future] = None

    # Derive goal if not explicitly provided
    goal = req.goal
    if not goal or not goal.strip():
        entities = rag_engine.extract_invoice_entities()
        vendor = entities.vendor or "Company X"
        amount = entities.amount if entities.amount is not None else 450.75
        due_date = entities.due_date or "2026-11-15"
        goal = (
            f"Navigate to http://127.0.0.1:8000, enter {vendor} into v_name, "
            f"input {amount:.2f} into v_amt, set v_date to {due_date}, "
            f"execute submit_invoice_btn, and verify the record is saved correctly."
        )

    active_sessions[session_id] = {
        "queue": event_queue,
        "hitl_future": None,
        "status": "running",
        "goal": goal,
        "auto_approve": req.auto_approve
    }

    async def on_event(event_type: str, data: dict):
        q = active_sessions.get(session_id, {}).get("queue")
        if q:
            await q.put({"event": event_type, "data": data})

    async def hitl_handler(action_name: str, payload: dict) -> bool:
        if req.auto_approve:
            return True
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        active_sessions[session_id]["hitl_future"] = future
        # Await decision from POST /api/agent/hitl
        try:
            approved = await asyncio.wait_for(future, timeout=300.0) # 5 min timeout
            return approved
        except asyncio.TimeoutError:
            return False

    async def run_in_background():
        try:
            agent = AutonomousAgentEngine(
                llm_client=llm_client,
                on_event=on_event,
                hitl_handler=hitl_handler,
                headless=False
            )
            success = await agent.run_task(goal=goal, max_steps=req.max_steps)
            active_sessions[session_id]["status"] = "finished"
        except Exception as e:
            await on_event("FATAL_ERROR", {"error": str(e)})
            active_sessions[session_id]["status"] = "error"
        finally:
            await on_event("STREAM_END", {})

    asyncio.create_task(run_in_background())

    return {
        "status": "started",
        "session_id": session_id,
        "goal": goal
    }

@app.get("/api/agent/events/{session_id}")
async def stream_agent_events(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    queue: asyncio.Queue = active_sessions[session_id]["queue"]

    async def event_generator():
        while True:
            try:
                event_data = await asyncio.wait_for(queue.get(), timeout=35.0)
                event_name = event_data.get("event", "message")
                payload = json.dumps(event_data.get("data", {}))
                yield f"event: {event_name}\ndata: {payload}\n\n"
                
                if event_name == "STREAM_END":
                    break
            except asyncio.TimeoutError:
                # Keep-alive heartbeat comment
                yield ": keepalive\n\n"
            except Exception:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/api/agent/hitl")
async def resolve_hitl(decision: HitlDecision):
    session = active_sessions.get(decision.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    future = session.get("hitl_future")
    if not future or future.done():
        raise HTTPException(status_code=400, detail="No pending HITL authorization request")

    future.set_result(decision.approved)
    return {"status": "resolved", "approved": decision.approved}

# ----------------------------------------------------------------
# Database Ledger & System Status Endpoints
# ----------------------------------------------------------------
@app.get("/api/invoices")
async def get_ledger_records():
    await ensure_ledger_running()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://127.0.0.1:8000/api/invoices", timeout=3.0)
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return []

@app.delete("/api/invoices/reset")
async def reset_ledger_proxy():
    """Proxy reset to the internal ledger server."""
    await ensure_ledger_running()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.delete("http://127.0.0.1:8000/api/invoices/reset", timeout=3.0)
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return {"status": "error", "message": "Could not reach ledger server"}

@app.get("/api/system-status")
async def get_system_status():
    ledger_online = False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://127.0.0.1:8000/api/invoices", timeout=1.5)
            ledger_online = (r.status_code == 200)
    except Exception:
        pass

    ollama_online = llm_client.is_ollama_available()
    gemini_available = bool(llm_client.gemini_api_key)

    if ollama_online:
        model_display = llm_client.model_name
        llm_status = "connected"
    elif gemini_available:
        model_display = "Gemini 2.0 Flash (API Fallback)"
        llm_status = "gemini-fallback"
    else:
        model_display = "Heuristic Planner (Offline Mode)"
        llm_status = "offline-heuristic"

    return {
        "ledger_server": "online" if ledger_online else "offline",
        "ledger_url": "http://127.0.0.1:8000",
        "ollama_status": llm_status,
        "active_model": model_display,
        "rag_chunks_loaded": len(rag_engine.chunks)
    }

# Mount static frontend
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("  🚀 CentrAlign AI Autonomous Task Platform Live")
    print("  👉 CentrAlign Autonomous Workspace: http://127.0.0.1:8500")
    print("  👉 Internal Ledger Hub:         http://127.0.0.1:8000")
    print("="*70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8500)
