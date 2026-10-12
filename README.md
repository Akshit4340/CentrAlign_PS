# CentrAlign AI — Autonomous Task Worker & Multimodal RAG Platform

> Built for the **CentrAlign AI Engineering Intern Problem Statement**: *Autonomous AI Task Worker capable of taking natural language goals, reading multiformat documents (PDFs & images), planning actions, executing workflows using a computer/browser, recovering from failures, obtaining human approval for critical operations, and verifying outcomes.*

---

## 🌟 Key Features

1. **Local-First LLM Architecture (Ollama + Qwen)**
   - Powered primarily by **Ollama** running local open-weights reasoning models (e.g., `qwen2.5-coder:7b` / `qwen2.7:7b`).
   - Ensures private, low-latency, and cost-free local autonomous decision-making.
   - Resilient multi-tier fallback routing: **Local Ollama** &rarr; **Cloud API** (Gemini 2.0 Flash / OpenAI) &rarr; **Dynamic Semantic DOM Introspection Engine** (offline rule-based reasoning).

2. **Awwwards-Caliber Minimalist Workspace** (`http://127.0.0.1:8500`)
   - High-end editorial aesthetic built on architectural off-white (`#F4F4F0`) and rich charcoal (`#111111`).
   - Anti-AI design: strictly no glowing gradient blobs, no drop shadows, and no glassmorphism.
   - Dual Operational Modes:
     - ⚡ **Autonomous AI Task Worker**: Accepts natural language goals, extracts entities, operates the browser, and executes workflows.
     - 🔍 **Grounded Multimodal RAG QA**: Ingests invoices/contracts and answers complex queries with chunk-level citations and grounded entity extraction.

3. **Advanced Multimodal RAG Engine (`src/advanced_rag.py`)**
   - **Document Parsers**: Native PDF parsing (`pypdf`), visual image analysis (`PIL`), and text loaders.
   - **Semantic Chunking**: Context-aware window chunking with sentence preservation and overlap.
   - **Hybrid Retrieval**: BM25 keyword matching + Dense semantic vector similarity + Domain entity re-ranking.
   - **Structured Entity Extraction**: Automatically extracts `Vendor Name`, `Total Amount`, `Due Date`, and `Invoice Number` with confidence scoring.

4. **Autonomous Task Execution & Computer Use (`src/agent_loop.py`)**
   - Strict **ReAct (Reasoning &rarr; Action &rarr; Observation &rarr; Verify)** loop.
   - Autonomous browser automation using **Playwright** against internal corporate applications (`http://127.0.0.1:8000`).
   - Dynamic DOM accessibility snapshots and semantic selector matching.
   - Self-correction with exponential backoff on transient errors and duplicate action detection.

5. **Interactive Human-in-the-Loop (HITL) Privilege Gate**
   - Pauses before sensitive actions (e.g., clicking commit/submit buttons to write financial transactions).
   - In Web UI: Dedicated authorization plaque with **Authorize** and **Abort** buttons and payload inspection.
   - In CLI: Terminal authorization prompt (`approve`).

6. **Outcome Verification & Audit Ledger**
   - Independent verification step calling the backend database API (`/api/invoices`).
   - Validates that the record was persisted in SQLite (`company_vault.db`).
   - Real-time live table view of database rows with dedup constraints and reset controls.

---

## 🚀 Quick Start Guide

### 1. Start Local Ollama LLM
Ensure Ollama is running and your model is pulled:
```bash
# Pull and start your preferred Qwen model (qwen2.5-coder:7b or qwen2.7:7b)
ollama pull qwen2.5-coder:7b
ollama serve
```

### 2. Setup Environment
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements (if not already installed)
pip install -r requirements.txt
```

### 3. Configure Model (`.env`)
```bash
# In .env:
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
TARGET_APP_URL=http://127.0.0.1:8000
```

### 4. Launch the Platform
Start the unified platform with a single command:
```bash
python web_server.py
```
- Open **CentrAlign AI Workspace**: [http://127.0.0.1:8500](http://127.0.0.1:8500)
- Internal Company Ledger Hub is running at: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🧪 Test Scenarios in the Web UI

### Scenario A: 1-Click Autonomous Invoice Entry (CentrAlign PS)
1. Click any benchmark sample: **Company X (PDF: $450.75)** or **Company X (Image Receipt)**.
2. Notice the instant Advanced RAG extraction displaying `Vendor: Company X`, `Amount: $450.75`, `Due Date: 2026-11-15`.
3. Click the **Execute (→)** button.
4. Watch the right-hand **Agent Monitor**:
   - The agent navigates to `http://127.0.0.1:8000`.
   - Types `Company X` into the vendor input field.
   - Types `450.75` into the amount input field.
   - Types `2026-11-15` into the due date input field.
   - **HITL Gate Triggers**: An interactive card appears asking to authorize the transaction commit.
   - Click **"Authorize Transaction"**.
   - The agent commits the record and executes `verify_outcome`.
   - The **VERIFICATION SUCCESS** banner appears!
5. Switch to the **Ledger Records** tab to see the verified transaction in `company_vault.db`.

### Scenario B: Grounded Multimodal RAG QA
1. Toggle the mode to **Document QA**.
2. Ask questions such as:
   - *"What is the total balance due and when is the payment date?"*
   - *"Who is the vendor and what service was provided?"*
   - *"Summarize the payment terms and line items."*
3. The system returns grounded responses with citations and relevance scores.

### Scenario C: Evaluation & Exploit Suite
Run the automated test suite testing entity precision and security containment against prompt injections:
```bash
python test_evals.py
```

---

## 📁 Repository Structure

```
CentrAlign/
├── app.py                   # Internal Company Ledger Hub (FastAPI, SQLite, Dedup & Reset)
├── web_server.py            # CentrAlign Platform Server (FastAPI, SSE, RAG API, Proxy)
├── main.py                  # CLI Autonomous Agent Runner
├── requirements.txt         # Project dependencies
├── company_vault.db         # SQLite persistent transaction storage
├── .env.example             # Environment configuration template
├── config/
│   └── prompt.py            # ReAct System Prompts & Available Tools schema
├── src/
│   ├── advanced_rag.py      # Multi-modal PDF/Image RAG Engine & Entity Extractor
│   ├── agent_loop.py        # Autonomous ReAct Agent Loop with SSE & HITL hooks
│   ├── browser_tools.py     # Playwright automation tools (navigate, type, click, verify)
│   ├── llm_client.py        # Unified LLM Client (Ollama Qwen + Cloud fallback + Semantic DOM Engine)
│   └── create_samples.py    # Test invoice generator (PDF & image)
├── static/
│   ├── index.html           # Editorial single-page application
│   ├── style.css            # Minimalist architectural design system
│   └── app.js               # Client controller (SSE streaming, uploads, HITL, ledger)
├── samples/                 # Sample benchmark invoices (PDFs & images)
└── instructions/            # CentrAlign AI Hiring Problem Statement documentation
```

---

## 🛡️ Evaluation Criteria Alignment

| Criteria | Implementation Evidence |
| :--- | :--- |
| **Autonomy** | Agent autonomously plans sequential actions via local Ollama LLM (`qwen2.5-coder:7b`) based on active DOM accessibility snapshots. |
| **Execution** | Real browser interaction via Playwright filling input forms and clicking DOM nodes. |
| **Reliability** | Exponential backoff for transient timeouts, duplicate action loop prevention, database dedup constraints. |
| **Verification** | Outcome verification checks actual SQLite database rows via `/api/invoices`, not simulated UI assertions. |
| **Human-In-The-Loop** | Explicit privilege gate interrupts execution before transaction commit until human approval is received. |
| **Multimodal RAG** | Ingests PDF and image invoices, chunks text, builds sparse+dense hybrid indices, and extracts structured entities. |
