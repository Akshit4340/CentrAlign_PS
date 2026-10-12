// static/app.js - CentrAlign AI Client Logic & Editorial Rendering
let currentMode = 'agent';
let activeSessionId = null;
let currentEventSource = null;
let activeDocument = null;

document.addEventListener('DOMContentLoaded', () => {
  checkSystemStatus();
  setInterval(checkSystemStatus, 6000);
  fetchLedgerRecords();
  setupDragAndDrop();
});

// -------------------------------------------------------------
// Mode and Tab Switching
// -------------------------------------------------------------
function setMode(mode) {
  currentMode = mode;
  document.getElementById('btnModeAgent').classList.toggle('active', mode === 'agent');
  document.getElementById('btnModeRag').classList.toggle('active', mode === 'rag');
  
  const input = document.getElementById('promptInput');
  if (mode === 'agent') {
    input.placeholder = "Enter task directive (e.g. 'Extract Company X invoice and commit to ledger at :8000')...";
  } else {
    input.placeholder = "Enter inquiry (e.g. 'What is the payment due date and total amount?')...";
  }
}

function switchTab(tab) {
  document.getElementById('tabBtnAgent').classList.toggle('active', tab === 'agent');
  document.getElementById('tabBtnLedger').classList.toggle('active', tab === 'ledger');
  document.getElementById('tabBtnSpecs').classList.toggle('active', tab === 'specs');

  document.getElementById('tabAgentContent').style.display = tab === 'agent' ? 'flex' : 'none';
  document.getElementById('tabLedgerContent').style.display = tab === 'ledger' ? 'flex' : 'none';
  document.getElementById('tabSpecsContent').style.display = tab === 'specs' ? 'flex' : 'none';

  if (tab === 'ledger') {
    fetchLedgerRecords();
  }
}

// -------------------------------------------------------------
// System Status Polling
// -------------------------------------------------------------
async function checkSystemStatus() {
  try {
    const res = await fetch('/api/system-status');
    if (!res.ok) return;
    const data = await res.json();
    
    // Ledger indicator
    const ledgerIndicator = document.getElementById('ledgerIndicator');
    const ledgerText = document.getElementById('ledgerStatusText');
    if (data.ledger_server === 'online') {
      ledgerIndicator.className = 'status-indicator';
      ledgerText.innerText = 'Ledger: Online (:8000)';
    } else {
      ledgerIndicator.className = 'status-indicator red';
      ledgerText.innerText = 'Ledger: Offline';
    }

    // Model indicator
    const modelText = document.getElementById('modelStatusText');
    const modelIndicator = document.getElementById('modelIndicator');
    modelText.innerText = `Model: ${data.active_model}`;
    modelIndicator.className = 'status-indicator';
  } catch (err) {
    console.error('Status check error:', err);
  }
}

// -------------------------------------------------------------
// Sample Loaders & File Uploads
// -------------------------------------------------------------
async function loadSample(sampleType) {
  showLoadingInChat("Indexing benchmark invoice sample...");
  try {
    const formData = new FormData();
    formData.append('sample_type', sampleType);
    
    const res = await fetch('/api/load-sample', {
      method: 'POST',
      body: formData
    });
    
    const data = await res.json();
    removeLoadingFromChat();

    if (data.status === 'success') {
      activeDocument = data;
      displayDocumentBadge(data.filename, data.chunks_indexed, data.entities);
      
      const v = data.entities.vendor || "Company X";
      const amt = data.entities.amount ? `$${data.entities.amount.toFixed(2)}` : "N/A";
      const dt = data.entities.due_date || "N/A";

      appendAssistantMessage(`
        Loaded benchmark document <strong>${data.filename}</strong> into hybrid RAG memory.
        <br><br>
        <strong>Extracted Document Entities:</strong>
        <ul>
          <li><strong>Vendor:</strong> ${v}</li>
          <li><strong>Amount Due:</strong> ${amt}</li>
          <li><strong>Payment Terms:</strong> ${dt}</li>
          <li><strong>Extraction Confidence:</strong> ${Math.round(data.entities.confidence * 100)}%</li>
        </ul>
        Ready to execute autonomous entry or answer grounded inquiries against this document.
      `);
      
      // Auto-populate task prompt
      document.getElementById('promptInput').value = `Extract ${v} invoice and enter it into the internal company ledger at http://127.0.0.1:8000`;
    }
  } catch (err) {
    removeLoadingFromChat();
    appendAssistantMessage(`Error loading sample: ${err.message}`);
  }
}

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  showLoadingInChat(`Ingesting and chunking ${file.name} with Hybrid RAG...`);

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    removeLoadingFromChat();

    if (data.status === 'success') {
      activeDocument = data;
      displayDocumentBadge(data.filename, data.chunks_indexed, data.entities);

      const v = data.entities.vendor || "Unknown";
      const amt = data.entities.amount ? `$${data.entities.amount.toFixed(2)}` : "Unknown";
      const dt = data.entities.due_date || "Unknown";

      appendAssistantMessage(`
        Document <strong>${data.filename}</strong> indexed successfully (${data.chunks_indexed} chunks created).
        <br><br>
        <strong>Extracted Document Entities:</strong>
        <ul>
          <li><strong>Vendor:</strong> ${v}</li>
          <li><strong>Total Amount:</strong> ${amt}</li>
          <li><strong>Due Date:</strong> ${dt}</li>
          <li><strong>Extraction Confidence:</strong> ${Math.round(data.entities.confidence * 100)}%</li>
        </ul>
        Ready to process form entry or address queries.
      `);

      if (v !== "Unknown") {
        document.getElementById('promptInput').value = `Enter ${v} invoice (${amt}, due ${dt}) into internal system`;
      }
    }
  } catch (err) {
    removeLoadingFromChat();
    appendAssistantMessage(`Upload error: ${err.message}`);
  }
}

function setupDragAndDrop() {
  const zone = document.getElementById('uploadZone');
  ['dragenter', 'dragover'].forEach(eventName => {
    zone.addEventListener(eventName, (e) => {
      e.preventDefault();
      zone.classList.add('drag-active');
    }, false);
  });
  ['dragleave', 'drop'].forEach(eventName => {
    zone.addEventListener(eventName, (e) => {
      e.preventDefault();
      zone.classList.remove('drag-active');
    }, false);
  });
  zone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      document.getElementById('fileInput').files = files;
      handleFileUpload({ target: { files: files } });
    }
  });
}

function displayDocumentBadge(filename, chunksCount, entities) {
  const badge = document.getElementById('activeDocBadge');
  badge.style.display = 'flex';
  document.getElementById('docBadgeName').querySelector('span').innerText = filename;
  document.getElementById('docBadgeStats').innerText = `Indexed into ${chunksCount} Chunks`;

  document.getElementById('entVendor').innerText = entities.vendor || 'N/A';
  document.getElementById('entAmount').innerText = entities.amount ? `$${entities.amount.toFixed(2)}` : 'N/A';
  document.getElementById('entDueDate').innerText = entities.due_date || 'N/A';
  document.getElementById('entConf').innerText = `${Math.round((entities.confidence || 0) * 100)}%`;
}

// -------------------------------------------------------------
// Chat and Query Submission
// -------------------------------------------------------------
function handleKeyDown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    submitUserQuery();
  }
}

async function submitUserQuery() {
  const input = document.getElementById('promptInput');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  appendUserMessage(text);

  if (currentMode === 'rag') {
    await executeRagQuery(text);
  } else {
    await executeAutonomousAgent(text);
  }
}

// -------------------------------------------------------------
// Advanced RAG QA Execution
// -------------------------------------------------------------
async function executeRagQuery(query) {
  showLoadingInChat("Searching hybrid chunks with BM25 + dense semantic embeddings...");

  try {
    const res = await fetch('/api/rag/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });
    const data = await res.json();
    removeLoadingFromChat();

    let citationsHtml = '';
    if (data.citations && data.citations.length > 0) {
      citationsHtml = `
        <div class="citations-strip">
          <span class="citations-label">Grounded Sources &amp; Retrieved Chunks:</span>
          ${data.citations.map(c => `
            <div class="citation-chip">
              <strong>${c.source} (Page ${c.page})</strong> &bull; Relevance: ${Math.round(c.score * 100)}%<br>
              <em>"${escapeHtml(c.snippet)}"</em>
            </div>
          `).join('')}
        </div>
      `;
    }

    appendAssistantMessage(`
      <div>${formatMarkdown(data.answer)}</div>
      ${citationsHtml}
    `);
  } catch (err) {
    removeLoadingFromChat();
    appendAssistantMessage(`RAG Error: ${err.message}`);
  }
}

// -------------------------------------------------------------
// Autonomous Task Worker Execution & Live Streaming
// -------------------------------------------------------------
async function executeAutonomousAgent(goal) {
  switchTab('agent');
  resetAgentTelemetry();

  const autoApprove = document.getElementById('chkAutoApprove').checked;

  appendAssistantMessage(`
    <strong>Autonomous Task Initialized</strong>: <em>${escapeHtml(goal)}</em>
    <br><br>
    The agent is executing the ReAct cycle (Reason &rarr; Act &rarr; Observe &rarr; Verify) inside the browser. Telemetry trace and viewport captures are streaming to the monitor.
  `);

  try {
    const res = await fetch('/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        goal: goal,
        auto_approve: autoApprove,
        max_steps: 10
      })
    });
    const data = await res.json();
    activeSessionId = data.session_id;

    connectAgentEvents(activeSessionId);
  } catch (err) {
    appendAssistantMessage(`Agent Initiation Error: ${err.message}`);
  }
}

function connectAgentEvents(sessionId) {
  if (currentEventSource) {
    currentEventSource.close();
  }

  currentEventSource = new EventSource(`/api/agent/events/${sessionId}`);

  currentEventSource.addEventListener('STEP_START', (e) => {
    const data = JSON.parse(e.data);
    document.getElementById('browserUrlBar').innerText = `Viewport: ${data.url}`;
    document.getElementById('stepCounterBadge').innerText = `Step: ${data.step}`;
  });

  currentEventSource.addEventListener('STEP_DECISION', (e) => {
    const data = JSON.parse(e.data);
    addStepToTimeline(data.step, data.thought, data.action, data.payload);
  });

  currentEventSource.addEventListener('HITL_REQUIRED', (e) => {
    const data = JSON.parse(e.data);
    showHitlPrompt(data);
  });

  currentEventSource.addEventListener('HITL_RESOLVED', (e) => {
    const data = JSON.parse(e.data);
    hideHitlPrompt();
    if (!data.approved) {
      appendAssistantMessage("Transaction authorization withheld by human operator. Execution aborted for safety.");
    }
  });

  currentEventSource.addEventListener('STEP_OBSERVATION', (e) => {
    const data = JSON.parse(e.data);
    updateStepObservation(data.step, data.observation);
    if (data.screenshot) {
      document.getElementById('browserScreenImg').src = `data:image/jpeg;base64,${data.screenshot}`;
    }
  });

  currentEventSource.addEventListener('TASK_FINISHED', (e) => {
    const data = JSON.parse(e.data);
    if (data.success) {
      showVerificationSuccess();
      appendAssistantMessage(`
        <strong>Task Execution Complete</strong>
        <br>
        Transaction record confirmed and verified against the backend SQLite ledger. View records in the Ledger tab.
      `);
      fetchLedgerRecords();
    } else {
      appendAssistantMessage(`Task ended without full verification. Inspect execution trace.`);
    }
    currentEventSource.close();
  });

  currentEventSource.addEventListener('FATAL_ERROR', (e) => {
    const data = JSON.parse(e.data);
    appendAssistantMessage(`Fatal execution error: ${data.error}`);
    currentEventSource.close();
  });

  currentEventSource.onerror = () => {
    currentEventSource.close();
  };
}

// -------------------------------------------------------------
// Human-In-The-Loop (HITL) Authorization
// -------------------------------------------------------------
function showHitlPrompt(data) {
  const card = document.getElementById('hitlCard');
  card.style.display = 'flex';
  document.getElementById('hitlDesc').innerHTML = `
    The agent is about to execute sensitive action:
    <strong>${escapeHtml(data.action)}</strong> with payload:
    <code style="background:var(--bg-canvas); padding:2px 6px; border:var(--border-hairline); font-family:var(--font-mono); color:var(--ink-primary);">
      ${escapeHtml(JSON.stringify(data.payload))}
    </code>
    <br>Do you authorize committing this transaction to the ledger?
  `;
}

function hideHitlPrompt() {
  document.getElementById('hitlCard').style.display = 'none';
}

async function resolveHitl(approved) {
  if (!activeSessionId) return;
  hideHitlPrompt();
  try {
    await fetch('/api/agent/hitl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: activeSessionId,
        approved: approved
      })
    });
  } catch (err) {
    console.error('HITL resolution error:', err);
  }
}

// -------------------------------------------------------------
// Telemetry UI Updates
// -------------------------------------------------------------
function resetAgentTelemetry() {
  document.getElementById('stepsTimeline').innerHTML = '';
  document.getElementById('verifBanner').style.display = 'none';
  document.getElementById('hitlCard').style.display = 'none';
  document.getElementById('stepCounterBadge').innerText = 'Step: 0';
}

function addStepToTimeline(step, thought, action, payload) {
  const timeline = document.getElementById('stepsTimeline');
  const stepId = `step_item_${step}`;
  
  const stepEl = document.createElement('div');
  stepEl.id = stepId;
  stepEl.className = 'step-item active';
  stepEl.innerHTML = `
    <div class="step-top">
      <span class="step-badge">STEP ${String(step).padStart(2, '0')}</span>
      <span class="step-action-pill">${escapeHtml(action)}(${escapeHtml(JSON.stringify(payload))})</span>
    </div>
    <div class="step-thought"><strong>Thought //</strong> ${escapeHtml(thought)}</div>
    <div class="step-observation" id="obs_${step}">Executing in browser viewport...</div>
  `;
  timeline.appendChild(stepEl);
  timeline.scrollTop = timeline.scrollHeight;
}

function updateStepObservation(step, observation) {
  const obsEl = document.getElementById(`obs_${step}`);
  if (obsEl) {
    obsEl.innerText = `Observation // ${observation}`;
  }
  const stepEl = document.getElementById(`step_item_${step}`);
  if (stepEl) {
    stepEl.classList.remove('active');
    if (observation.includes('VERIFICATION_SUCCESS')) {
      stepEl.classList.add('success');
    }
  }
}

function showVerificationSuccess() {
  const banner = document.getElementById('verifBanner');
  banner.style.display = 'grid';
}

// -------------------------------------------------------------
// Live Database Ledger Table
// -------------------------------------------------------------
async function fetchLedgerRecords() {
  try {
    const res = await fetch('/api/invoices');
    if (!res.ok) return;
    const records = await res.json();
    const tbody = document.getElementById('ledgerTableBody');
    
    if (!records || records.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--ink-muted); padding:24px; font-family:var(--font-mono);">No audited transactions found in database.</td></tr>';
      return;
    }

    tbody.innerHTML = records.map(r => `
      <tr>
        <td style="font-family:var(--font-mono); font-weight:600; color:var(--accent-rust);">#${String(r.id).padStart(3, '0')}</td>
        <td style="font-weight:500;">${escapeHtml(r.vendor)}</td>
        <td style="font-family:var(--font-mono); font-weight:600;">$${parseFloat(r.amount).toFixed(2)}</td>
        <td style="font-family:var(--font-mono); color:var(--ink-secondary);">${escapeHtml(r.due_date)}</td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Fetch ledger error:', err);
  }
}

async function resetLedger() {
  if (!confirm('Clear all invoice records from the ledger database?')) return;
  try {
    await fetch('/api/invoices/reset', { method: 'DELETE' });
    appendAssistantMessage('Ledger database cleared. All records purged.');
    fetchLedgerRecords();
  } catch (err) {
    appendAssistantMessage(`Reset error: ${err.message}`);
  }
}

// -------------------------------------------------------------
// Chat Utilities
// -------------------------------------------------------------
function appendUserMessage(text) {
  const thread = document.getElementById('chatThread');
  const msgEl = document.createElement('div');
  msgEl.className = 'chat-message user';
  msgEl.innerHTML = `
    <div class="msg-header-row">
      <span>[OPERATOR // DIRECTIVE]</span>
    </div>
    <div class="msg-body">
      <div class="msg-bubble">${escapeHtml(text)}</div>
    </div>
  `;
  thread.appendChild(msgEl);
  thread.scrollTop = thread.scrollHeight;
}

function appendAssistantMessage(htmlContent) {
  const thread = document.getElementById('chatThread');
  const msgEl = document.createElement('div');
  msgEl.className = 'chat-message assistant';
  msgEl.innerHTML = `
    <div class="msg-header-row">
      <span>[SYSTEM // AGENT]</span>
    </div>
    <div class="msg-body">
      <div class="msg-bubble">${htmlContent}</div>
    </div>
  `;
  thread.appendChild(msgEl);
  thread.scrollTop = thread.scrollHeight;
}

function showLoadingInChat(text) {
  removeLoadingFromChat();
  const thread = document.getElementById('chatThread');
  const msgEl = document.createElement('div');
  msgEl.id = 'chatLoadingIndicator';
  msgEl.className = 'chat-message assistant';
  msgEl.innerHTML = `
    <div class="msg-header-row">
      <span>[PROCESSING // REASONING]</span>
    </div>
    <div class="msg-body">
      <div class="msg-bubble" style="color:var(--ink-secondary); font-family:var(--font-mono); font-size:0.78rem;">
        &bull; ${escapeHtml(text)}
      </div>
    </div>
  `;
  thread.appendChild(msgEl);
  thread.scrollTop = thread.scrollHeight;
}

function removeLoadingFromChat() {
  const el = document.getElementById('chatLoadingIndicator');
  if (el) el.remove();
}

function formatMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/^### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^## (.*$)/gim, '<h3>$1</h3>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/\n\n/gim, '<br><br>')
    .replace(/\n- (.*)/gim, '<br>&bull; $1');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
