const INVENTORY_GRID = document.getElementById("inventory-grid");
const CRAFT_BTN = document.getElementById("craft-btn");
const FUEL_FILL = document.getElementById("fuel-fill");
const FUEL_TEXT = document.getElementById("fuel-text");

let dragSource = null;

const ITEM_COLORS = {
  "minecraft:dirt": "#8B4513",
  "minecraft:stone": "#808080",
  "minecraft:cobblestone": "#606060",
  "minecraft:oak_planks": "#C4A882",
  "minecraft:bedrock": "#333333",
  "minecraft:coal": "#1a1a1a",
  "minecraft:iron_ingot": "#d4d4d4",
  "minecraft:gold_ingot": "#FFD700",
  "minecraft:diamond": "#4FC3F7",
  "minecraft:stick": "#8B7355",
  "minecraft:crafting_table": "#C4A882",
};

function getItemColor(name) {
  return ITEM_COLORS[name] || null;
}

function shortenName(name) {
  if (!name) return "";
  const parts = name.split(":");
  if (parts.length === 2) return parts[1].replace(/_/g, " ");
  return name.replace(/_/g, " ");
}

function clearDragOver() {
  document.querySelectorAll(".slot-drag-over").forEach(el => el.classList.remove("slot-drag-over"));
}

function attachDragEvents(el, slotNum) {
  el.setAttribute("draggable", "true");

  el.addEventListener("dragstart", function (e) {
    if (!this.classList.contains("slot-filled")) {
      e.preventDefault();
      return;
    }
    dragSource = slotNum;
    this.classList.add("slot-drag-source");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(slotNum));
  });

  el.addEventListener("dragend", function () {
    document.querySelectorAll(".slot-drag-source").forEach(el => el.classList.remove("slot-drag-source"));
    clearDragOver();
    dragSource = null;
  });

  el.addEventListener("dragover", function (e) {
    if (dragSource === null || dragSource === slotNum) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  });

  el.addEventListener("dragenter", function () {
    if (dragSource === null || dragSource === slotNum) return;
    this.classList.add("slot-drag-over");
  });

  el.addEventListener("dragleave", function () {
    this.classList.remove("slot-drag-over");
  });

  el.addEventListener("drop", function (e) {
    e.preventDefault();
    clearDragOver();
    if (dragSource === null || dragSource === slotNum) return;
    const src = dragSource;
    const tgt = slotNum;
    dragSource = null;
    document.querySelectorAll(".slot-drag-source").forEach(el => el.classList.remove("slot-drag-source"));
    transferSlots(src, tgt);
  });

  el.addEventListener("click", function () {
    selectSlot(slotNum);
  });
}

async function transferSlots(source, target) {
  try {
    await fetch("/inventory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "select", slot: source }),
    });
    await fetch("/inventory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "transfer", slot: target }),
    });
  } catch (_) {}
}

function renderInventory(data) {
  if (!data || !data.slots) return;
  const selected = data.selected_slot || 1;

  INVENTORY_GRID.innerHTML = "";
  for (let i = 0; i < 16; i++) {
    const slotNum = i + 1;
    const item = data.slots[i] || null;
    const div = document.createElement("div");
    div.className = "slot";
    if (slotNum === selected) div.classList.add("slot-selected");
    if (item) div.classList.add("slot-filled");

    const numEl = document.createElement("span");
    numEl.className = "slot-num";
    numEl.textContent = slotNum;
    div.appendChild(numEl);

    if (item && item.name) {
      const color = getItemColor(item.name);
      if (color) div.style.borderColor = color;
      const nameEl = document.createElement("span");
      nameEl.className = "slot-name";
      nameEl.textContent = shortenName(item.name);
      div.appendChild(nameEl);
      if (item.count && item.count > 1) {
        const countEl = document.createElement("span");
        countEl.className = "slot-count";
        countEl.textContent = item.count;
        div.appendChild(countEl);
      }
    }

    div.setAttribute("data-slot", slotNum);
    attachDragEvents(div, slotNum);
    INVENTORY_GRID.appendChild(div);
  }

  for (let j = 0; j < 4; j++) {
    const cs = document.querySelector('#crafting-grid .slot[data-slot="' + (j + 1) + '"]');
    if (!cs) continue;
    const item = data.slots[j] || null;
    cs.className = "slot";
    cs.setAttribute("draggable", "true");
    if (item) {
      cs.classList.add("slot-filled");
      cs.innerHTML = "";
      const numEl = document.createElement("span");
      numEl.className = "slot-num";
      numEl.textContent = j + 1;
      cs.appendChild(numEl);
      const nameEl = document.createElement("span");
      nameEl.className = "slot-name";
      nameEl.textContent = item.name ? shortenName(item.name) : "?";
      cs.appendChild(nameEl);
      if (item.count && item.count > 1) {
        const countEl = document.createElement("span");
        countEl.className = "slot-count";
        countEl.textContent = item.count;
        cs.appendChild(countEl);
      }
    } else {
      cs.innerHTML = "";
      const numEl = document.createElement("span");
      numEl.className = "slot-num";
      numEl.textContent = j + 1;
      cs.appendChild(numEl);
    }
    // Re-attach drag events (they get reset when innerHTML is wiped)
    const newCs = document.querySelector('#crafting-grid .slot[data-slot="' + (j + 1) + '"]');
    if (newCs) attachDragEvents(newCs, j + 1);
  }

  if (data.fuel) updateFuel(data.fuel);
}

function updateFuel(fuel) {
  const level = typeof fuel.level === "number" ? fuel.level : 0;
  const limit = typeof fuel.limit === "number" ? fuel.limit : 0;
  const pct = limit > 0 ? Math.min(100, (level / limit) * 100) : 0;
  FUEL_FILL.style.width = pct + "%";
  FUEL_TEXT.textContent = level + " / " + limit;
}

async function selectSlot(slot) {
  try {
    await fetch("/inventory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "select", slot: slot }),
    });
  } catch (_) {}
}

async function craft() {
  try {
    const resp = await fetch("/inventory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "craft", limit: 64 }),
    });
    const result = await resp.json();
    window.displayResult("POST /inventory {type: \"craft\"}", result, "craft");
    window.flashButton(CRAFT_BTN, resp.ok);
  } catch (err) {
    window.displayResult("POST /inventory {type: \"craft\"}", { error: err.message }, "craft");
    window.flashButton(CRAFT_BTN, false);
  }
}

CRAFT_BTN.addEventListener("click", craft);

async function fetchInventory() {
  try {
    const resp = await fetch("/inventory");
    if (!resp.ok) return;
    const data = await resp.json();
    renderInventory(data);
  } catch (_) {}
}

fetchInventory();
setInterval(fetchInventory, 2000);
setInterval(fetchInventory, 2000);
