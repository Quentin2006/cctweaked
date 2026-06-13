const AI = {
  sessionId: null,
  eventSource: null,
};

async function startSession() {
  const goal = document.getElementById("ai-goal-input").value.trim();
  if (!goal) return;

  const btn = document.getElementById("ai-start-btn");
  btn.disabled = true;
  btn.textContent = "Starting...";

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
    } else {
      addAIEvent("error", data.error || "HTTP " + resp.status);
      btn.disabled = false;
      btn.textContent = "Start";
    }
  } catch (err) {
    addAIEvent("error", err.message || "Network error");
    btn.disabled = false;
    btn.textContent = "Start";
  }
}

function connectStream(sessionId) {
  AI.eventSource = new EventSource("/api/ai/stream/" + sessionId);

  AI.eventSource.addEventListener("thought", function (e) {
    const data = JSON.parse(e.data);
    addAIEvent("thought", data.content);
  });
  AI.eventSource.addEventListener("action", function (e) {
    const data = JSON.parse(e.data);
    addAIEvent("action", data.method + " " + data.url);
  });
  AI.eventSource.addEventListener("result", function (e) {
    const data = JSON.parse(e.data);
    addAIEvent("result", JSON.stringify(data.body, null, 1));
  });
  AI.eventSource.addEventListener("question", function (e) {
    const data = JSON.parse(e.data);
    showAIQuestion(data.content, data.session_id);
  });
  AI.eventSource.addEventListener("done", function (e) {
    const data = JSON.parse(e.data);
    addAIEvent("done", data.content);
    endSession();
  });
  AI.eventSource.addEventListener("error", function (e) {
    const data = JSON.parse(e.data);
    addAIEvent("error", data.content);
    endSession();
  });
  AI.eventSource.addEventListener("progress", function (e) {
    const data = JSON.parse(e.data);
    updateAIProgress(data);
  });

  AI.eventSource.onerror = function () {
    addAIEvent("error", "Connection lost");
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
