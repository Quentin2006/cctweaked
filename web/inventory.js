const INVENTORY_GRID = document.getElementById("inventory-grid");
const CRAFT_BTN = document.getElementById("craft-btn");
const FUEL_FILL = document.getElementById("fuel-fill");
const FUEL_TEXT = document.getElementById("fuel-text");

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
  var parts = name.split(":");
  if (parts.length === 2) {
    return parts[1].replace(/_/g, " ");
  }
  return name.replace(/_/g, " ");
}

function renderInventory(data) {
  if (!data || !data.slots) return;

  var selected = data.selected_slot || 1;

  INVENTORY_GRID.innerHTML = "";
  for (var i = 0; i < 16; i++) {
    var slotNum = i + 1;
    var item = data.slots[i] || null;

    var div = document.createElement("div");
    div.className = "slot";
    if (slotNum === selected) div.classList.add("slot-selected");
    if (item) div.classList.add("slot-filled");

    var numEl = document.createElement("span");
    numEl.className = "slot-num";
    numEl.textContent = slotNum;
    div.appendChild(numEl);

    if (item && item.name) {
      var color = getItemColor(item.name);
      if (color) div.style.borderColor = color;

      var nameEl = document.createElement("span");
      nameEl.className = "slot-name";
      nameEl.textContent = shortenName(item.name);
      div.appendChild(nameEl);

      if (item.count && item.count > 1) {
        var countEl = document.createElement("span");
        countEl.className = "slot-count";
        countEl.textContent = item.count;
        div.appendChild(countEl);
      }
    }

    div.setAttribute("data-slot", slotNum);
    div.addEventListener("click", function () {
      var s = parseInt(this.getAttribute("data-slot"));
      selectSlot(s);
    });

    INVENTORY_GRID.appendChild(div);
  }

  for (var j = 0; j < 4; j++) {
    var cs = document.querySelector('#crafting-grid .slot[data-slot="' + (j + 1) + '"]');
    if (!cs) continue;
    var item = data.slots[j] || null;
    cs.className = "slot";
    if (item) {
      cs.classList.add("slot-filled");
      cs.innerHTML = "";
      var numEl = document.createElement("span");
      numEl.className = "slot-num";
      numEl.textContent = j + 1;
      cs.appendChild(numEl);
      var nameEl = document.createElement("span");
      nameEl.className = "slot-name";
      nameEl.textContent = item.name ? shortenName(item.name) : "?";
      cs.appendChild(nameEl);
      if (item.count && item.count > 1) {
        var countEl = document.createElement("span");
        countEl.className = "slot-count";
        countEl.textContent = item.count;
        cs.appendChild(countEl);
      }
    } else {
      cs.className = "slot";
      cs.innerHTML = "";
      var numEl = document.createElement("span");
      numEl.className = "slot-num";
      numEl.textContent = j + 1;
      cs.appendChild(numEl);
    }
  }

  if (data.fuel) updateFuel(data.fuel);
}

function updateFuel(fuel) {
  var level = typeof fuel.level === "number" ? fuel.level : 0;
  var limit = typeof fuel.limit === "number" ? fuel.limit : 0;
  var pct = limit > 0 ? Math.min(100, (level / limit) * 100) : 0;
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
    var resp = await fetch("/inventory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "craft", limit: 64 }),
    });
    var result = await resp.json();
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
    var resp = await fetch("/inventory");
    if (!resp.ok) return;
    var data = await resp.json();
    renderInventory(data);
  } catch (_) {}
}

fetchInventory();
setInterval(fetchInventory, 2000);
