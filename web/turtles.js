const TURTLE_API = "/api/turtles";
let selectedTurtleId = null;
let turtlePollInterval = null;

const FACING_NAMES = { 0: "North", 1: "East", 2: "South", 3: "West" };

async function loadTurtles() {
  try {
    const resp = await fetch(TURTLE_API);
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    const turtles = data.turtles || [];
    const select = document.getElementById("turtle-select");
    const dot = document.getElementById("turtle-status-dot");
    if (!select) return [];

    select.innerHTML = "";

    if (turtles.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Waiting for turtle...";
      select.appendChild(opt);
      if (dot) dot.className = "turtle-status-dot offline";
      hideTurtleInfo(true);
      return [];
    }

    turtles.forEach(function (t) {
      const opt = document.createElement("option");
      opt.value = t.id;
      opt.textContent = "Turtle #" + t.id + " (" + t.x + ", " + t.y + ", " + t.z + ")";
      select.appendChild(opt);
    });

    const saved = getSelectedTurtleId();
    if (saved && turtles.some(function (t) { return t.id === saved; })) {
      select.value = saved;
    } else {
      select.value = turtles[0].id;
    }
    selectTurtle(select.value);

    return turtles;
  } catch (_) {
    const select = document.getElementById("turtle-select");
    if (select) {
      select.innerHTML = '<option value="">Connection error</option>';
    }
    const dot = document.getElementById("turtle-status-dot");
    if (dot) dot.className = "turtle-status-dot offline";
    hideTurtleInfo(true);
    return [];
  }
}

function selectTurtle(turtleId) {
  selectedTurtleId = turtleId;
  if (turtleId) {
    localStorage.setItem("selectedTurtleId", turtleId);
  } else {
    localStorage.removeItem("selectedTurtleId");
  }
  updateTurtleInfo(turtleId);
}

function getSelectedTurtleId() {
  if (selectedTurtleId) return selectedTurtleId;
  var saved = localStorage.getItem("selectedTurtleId");
  if (saved) {
    selectedTurtleId = saved;
    return saved;
  }
  return null;
}

async function updateTurtleInfo(turtleId) {
  if (!turtleId) {
    hideTurtleInfo(true);
    return;
  }

  try {
    const resp = await fetch(TURTLE_API);
    if (!resp.ok) return;
    const data = await resp.json();
    const turtles = data.turtles || [];
    var turtle = null;
    for (var i = 0; i < turtles.length; i++) {
      if (turtles[i].id === turtleId) {
        turtle = turtles[i];
        break;
      }
    }

    if (!turtle) {
      hideTurtleInfo(true);
      return;
    }

    hideTurtleInfo(false);

    var pos = document.getElementById("turtle-position");
    var facing = document.getElementById("turtle-facing");
    var status = document.getElementById("turtle-status");
    var connected = document.getElementById("turtle-connected");
    var dot = document.getElementById("turtle-status-dot");

    if (pos) pos.textContent = turtle.x + ", " + turtle.y + ", " + turtle.z;
    if (facing) facing.textContent = FACING_NAMES[turtle.facing] || turtle.facing;
    if (status) status.textContent = turtle.status || "unknown";
    if (connected) connected.textContent = turtle.connected ? "Yes" : "No";

    if (dot) {
      dot.className = "turtle-status-dot";
      if (turtle.connected) {
        if (turtle.status === "busy") {
          dot.classList.add("busy");
        } else {
          dot.classList.add("connected");
        }
      } else {
        dot.classList.add("offline");
      }
    }
  } catch (_) {
    // Silently fail on poll errors — next poll will retry
  }
}

function hideTurtleInfo(hide) {
  var grid = document.getElementById("turtle-info-grid");
  if (grid) {
    if (hide) {
      grid.classList.add("turtle-hidden");
    } else {
      grid.classList.remove("turtle-hidden");
    }
  }
}

function startTurtlePolling(intervalMs) {
  if (intervalMs === undefined) intervalMs = 3000;
  if (turtlePollInterval) clearInterval(turtlePollInterval);
  turtlePollInterval = setInterval(loadTurtles, intervalMs);
}

function stopTurtlePolling() {
  if (turtlePollInterval) {
    clearInterval(turtlePollInterval);
    turtlePollInterval = null;
  }
}

document.addEventListener("DOMContentLoaded", function () {
  var select = document.getElementById("turtle-select");
  if (select) {
    select.addEventListener("change", function () {
      selectTurtle(this.value);
    });
  }
  loadTurtles().then(function () {
    startTurtlePolling(3000);
  });
});

document.addEventListener("visibilitychange", function () {
  if (document.hidden) {
    stopTurtlePolling();
  } else {
    loadTurtles().then(function () {
      startTurtlePolling(3000);
    });
  }
});
