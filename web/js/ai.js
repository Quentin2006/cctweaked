const AI = {
  sessionId: null,
  eventSource: null,
};

function updateAIStatus(status, type = "idle") {
  const el = document.getElementById("ai-status");
  if (!el) return;
  el.style.display = "block";
  el.textContent = status;
  const colors = {
    idle: "var(--text-dim)",
    running: "var(--accent-primary)",
    thinking: "var(--text-secondary)",
    acting: "var(--accent-primary)",
    waiting: "var(--accent-warning)",
    error: "var(--accent-danger)",
    done: "var(--accent-success)",
  };
  el.style.color = colors[type] || colors.idle;
}

async function startSession() {
  const goal = document.getElementById("ai-goal-input").value.trim();
  if (!goal) return;

  const btn = document.getElementById("ai-start-btn");
  btn.disabled = true;
  btn.textContent = "Starting...";
  updateAIStatus("Starting...", "running");

  try {
    const resp = await fetch("/api/ai/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal }),
    });
    const data = await resp.json();
    if (resp.ok) {
      AI.sessionId = data.session_id;
      connectStream(data.session_id);
      addAIEvent("system", 'Session started: "' + goal + '"');
      document.getElementById("ai-goal-input").value = "";
      document.getElementById("ai-cancel-btn").style.display = "inline-flex";
      updateAIStatus("Running", "running");
    } else {
      addAIEvent("error", data.error || "HTTP " + resp.status);
      btn.disabled = false;
      btn.textContent = "Start";
      updateAIStatus("Failed to start", "error");
    }
  } catch (err) {
    addAIEvent("error", err.message || "Network error");
    btn.disabled = false;
    btn.textContent = "Start";
    updateAIStatus("Error", "error");
  }
}

function connectStream(sessionId) {
  AI.eventSource = new EventSource("/api/ai/stream/" + sessionId);

  AI.eventSource.addEventListener("thought", function (e) {
    const data = JSON.parse(e.data);
    addAIEvent("thought", data.content);
    updateAIStatus("Thinking...", "thinking");
  });
  AI.eventSource.addEventListener("action", function (e) {
    const data = JSON.parse(e.data);
    const cmd = data.method || "";
    addAIEvent("action", cmd);
    updateAIStatus("Acting: " + cmd.slice(0, 40), "acting");
  });
  AI.eventSource.addEventListener("result", function (e) {
    const data = JSON.parse(e.data);
    addAIEvent("result", JSON.stringify(data.body, null, 1));
    updateAIStatus("Waiting...", "waiting");
  });
  AI.eventSource.addEventListener("question", function (e) {
    const data = JSON.parse(e.data);
    showAIQuestion(data.content, data.session_id);
    updateAIStatus("Question: " + data.content.slice(0, 40), "waiting");
  });
  AI.eventSource.addEventListener("done", function (e) {
    const data = JSON.parse(e.data);
    addAIEvent("done", data.content);
    updateAIStatus("Done", "done");
    endSession();
  });
  AI.eventSource.addEventListener("error", function (e) {
    const data = JSON.parse(e.data);
    addAIEvent("error", data.content);
    updateAIStatus("Error", "error");
    endSession();
  });
  AI.eventSource.addEventListener("progress", function (e) {
    const data = JSON.parse(e.data);
    updateAIProgress(data);
    updateAIStatus("Step " + data.step + " / " + (data.max_steps || 100), "running");
  });

  AI.eventSource.onerror = function () {
    addAIEvent("error", "Connection lost");
    updateAIStatus("Disconnected", "error");
    endSession();
  };
}

function addAIEvent(type, content) {
  const log = document.getElementById("ai-log");
  if (!log) return;
  const entry = document.createElement("div");
  entry.className = "ai-entry ai-" + type;

  const now = new Date();
  const ts =
    now.getHours().toString().padStart(2, "0") +
    ":" +
    now.getMinutes().toString().padStart(2, "0") +
    ":" +
    now.getSeconds().toString().padStart(2, "0");

  const empty = log.querySelector(".ai-empty");
  if (empty) empty.remove();

  entry.innerHTML =
    '<span class="ai-ts">[' + ts + ']</span> ' +
    '<span class="ai-content">' + escapeHtml(content) + '</span>';

  log.appendChild(entry);
  log.scrollTop = log.scrollHeight;
}

function showAIQuestion(question, sessionId) {
  const log = document.getElementById("ai-log");
  const entry = document.createElement("div");
  entry.className = "ai-entry ai-question";

  const empty = log.querySelector(".ai-empty");
  if (empty) empty.remove();

  entry.innerHTML =
    '<span class="ai-ts">[?]</span> ' +
    '<span class="ai-content">' + escapeHtml(question) + '</span>' +
    '<div class="ai-answer-row">' +
      '<input type="text" class="ai-answer-input" placeholder="Your answer..." />' +
      '<button class="ai-answer-btn">Send</button>' +
    '</div>';
  log.appendChild(entry);
  log.scrollTop = log.scrollHeight;

  const input = entry.querySelector(".ai-answer-input");
  const btn = entry.querySelector(".ai-answer-btn");

  async function sendAnswer() {
    const answer = input.value.trim();
    if (!answer) return;
    btn.disabled = true;
    try {
      await fetch("/api/ai/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, answer: answer }),
      });
      addAIEvent("system", "You: " + answer);
    } catch (err) {
      addAIEvent("error", "Failed to send answer");
    }
  }

  btn.addEventListener("click", sendAnswer);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendAnswer();
  });
  input.focus();
}

async function cancelSession() {
  if (!AI.sessionId) return;
  try {
    await fetch("/api/ai/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: AI.sessionId }),
    });
  } catch (_) {
    // best-effort
  }
  endSession();
}

function endSession() {
  if (AI.eventSource) {
    AI.eventSource.close();
    AI.eventSource = null;
  }
  AI.sessionId = null;
  document.getElementById("ai-start-btn").disabled = false;
  document.getElementById("ai-start-btn").textContent = "Start";
  document.getElementById("ai-cancel-btn").style.display = "none";
  updateAIStatus("Idle", "idle");
}

function updateAIProgress(data) {
  const el = document.getElementById("ai-progress");
  if (el) {
    el.textContent = "Step " + data.step + " / " + (data.max_steps || 100);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("ai-start-btn").addEventListener("click", startSession);
  document.getElementById("ai-cancel-btn").addEventListener("click", cancelSession);
  document.getElementById("ai-goal-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter") startSession();
  });
});
