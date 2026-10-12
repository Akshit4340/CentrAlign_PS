# app.py
import sqlite3
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Enterprise Record Vault Hub")
DB_PATH = "company_vault.db"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceSchema(BaseModel):
    vendor: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    due_date: str = Field(..., min_length=8)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT, amount REAL, due_date TEXT,
                UNIQUE(vendor, amount, due_date)
            )
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_inv_uniq
            ON invoices(vendor, amount, due_date)
        """)
init_db()

@app.post("/api/invoices")
async def create_invoice(invoice: InvoiceSchema):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Check for existing duplicate
        cursor.execute(
            "SELECT id FROM invoices WHERE vendor = ? AND amount = ? AND due_date = ?",
            (invoice.vendor, invoice.amount, invoice.due_date)
        )
        existing = cursor.fetchone()
        if existing:
            return {
                "status": "duplicate",
                "message": f"Invoice for {invoice.vendor} (${invoice.amount:.2f}, due {invoice.due_date}) already exists.",
                "invoice_id": existing[0]
            }

        cursor.execute("INSERT INTO invoices (vendor, amount, due_date) VALUES (?, ?, ?)",
                       (invoice.vendor, invoice.amount, invoice.due_date))
        conn.commit()
        return {"status": "success", "invoice_id": cursor.lastrowid}

@app.get("/api/invoices")
async def list_invoices():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT * FROM invoices").fetchall()]

@app.delete("/api/invoices/reset")
async def reset_ledger():
    """Clear all invoice records — useful for demo resets."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM invoices")
        conn.commit()
    return {"status": "success", "message": "All invoice records cleared."}

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Internal Ledger Processing Hub</title>
        <style>
            body { font-family: sans-serif; background: #0f172a; color: white; padding: 40px; }
            .box { background: #1e293b; padding: 24px; border-radius: 8px; max-width: 450px; margin: auto; }
            input, button { width: 100%; padding: 10px; margin-top: 10px; border-radius: 4px; box-sizing: border-box; }
            button { background: #0284c7; color: white; border: none; font-weight: bold; cursor: pointer; }
            .btn-danger { background: #dc2626; margin-top: 16px; }
        </style>
    </head>
    <body>
        <div class="box">
            <div style="background:#0f172a; padding:10px 14px; margin-bottom:14px; border-radius:6px; border:1px solid #38bdf8; font-size:13px; text-align:center;">
                <strong>CentrAlign AI Workspace:</strong> <a href="http://127.0.0.1:8500" target="_blank" style="color:#38bdf8; font-weight:bold; text-decoration:none;">Open Autonomous Workspace Platform (Port 8500) &rarr;</a>
            </div>
            <h2>Ledger Submission Panel</h2>
            <div id="status_msg">System Status: Awaiting Action</div>
            <input type="text" id="v_name" placeholder="Vendor Name">
            <input type="number" id="v_amt" placeholder="Amount">
            <input type="text" id="v_date" placeholder="Due Date (YYYY-MM-DD)">
            <button id="submit_invoice_btn" onclick="submitData()">Commit Transaction Record</button>
            <button class="btn-danger" onclick="resetLedger()">Reset All Records</button>
        </div>
        <script>
            async function submitData() {
                const payload = {
                    vendor: document.getElementById('v_name').value,
                    amount: parseFloat(document.getElementById('v_amt').value),
                    due_date: document.getElementById('v_date').value
                };
                const res = await fetch('/api/invoices', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                const msg = document.getElementById('status_msg');
                if(res.ok && data.status === 'success') {
                    msg.innerText = "System Status: Record Committed Successfully";
                    msg.style.color = "#4ade80";
                } else if(data.status === 'duplicate') {
                    msg.innerText = "System Status: Duplicate Record Detected";
                    msg.style.color = "#f59e0b";
                } else {
                    msg.innerText = "System Status: Processing Error Encountered";
                    msg.style.color = "#f87171";
                }
            }
            async function resetLedger() {
                if (!confirm('Clear all invoice records?')) return;
                await fetch('/api/invoices/reset', { method: 'DELETE' });
                document.getElementById('status_msg').innerText = 'System Status: Ledger Cleared';
                document.getElementById('status_msg').style.color = '#38bdf8';
            }
        </script>
    </body>
    </html>
    """

