var ACTION_ENDPOINT = "/action";

document.querySelectorAll(".dir-btn").forEach(function (btn) {
  btn.addEventListener("click", function () {
    document.querySelectorAll(".dir-btn").forEach(function (b) {
      b.classList.remove("active");
    });
    btn.classList.add("active");
  });
});

function getActiveDirection() {
  var active = document.querySelector(".dir-btn.active");
  return active ? active.getAttribute("data-dir") : "forward";
}

document.querySelectorAll(".action-btn").forEach(function (btn) {
  btn.addEventListener("click", async function () {
    var type = btn.getAttribute("data-action");
    var direction = getActiveDirection();
    var body = { type: type, direction: direction };
    var turtleId = typeof getSelectedTurtleId !== 'undefined' ? getSelectedTurtleId() : null;
    if (turtleId) body.turtle_id = turtleId;

    if (type === "place") {
      var selectedSlot = document.querySelector(".slot.slot-selected");
      if (selectedSlot) {
        var nameEl = selectedSlot.querySelector(".slot-name");
        if (nameEl) {
          body.block = nameEl.textContent.trim();
        }
      }
    }

    try {
      var resp = await fetch(ACTION_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      var result = await resp.json();

      if (resp.ok) {
        window.flashButton(btn, true);
        window.displayResult(
          "POST /action {type: \"" + type + "\", direction: \"" + direction + "\"}",
          result,
          "action"
        );
      } else {
        window.flashButton(btn, false);
        window.displayResult(
          "POST /action {type: \"" + type + "\", direction: \"" + direction + "\"}",
          { error: result.error || "HTTP " + resp.status },
          "action"
        );
      }
    } catch (err) {
      window.flashButton(btn, false);
      window.displayResult(
        "POST /action {type: \"" + type + "\", direction: \"" + direction + "\"}",
        { error: err.message || "Network error" },
        "action"
      );
    }
  });
});
