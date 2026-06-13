const MOVE_ENDPOINT = "/move";

document.querySelectorAll("[data-direction]").forEach(function (btn) {
  btn.addEventListener("click", async function () {
    const direction = btn.getAttribute("data-direction");
    const body = JSON.stringify({ direction: direction, distance: 1 });

    try {
      const resp = await fetch(MOVE_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
      });

      const result = await resp.json();

      if (resp.ok) {
        window.flashButton(btn, true);
        window.displayResult(
          "POST /move {direction: \"" + direction + "\", distance: 1}",
          result,
          "move"
        );
      } else {
        window.flashButton(btn, false);
        window.displayResult(
          "POST /move {direction: \"" + direction + "\", distance: 1}",
          { error: result.error || "HTTP " + resp.status },
          "move"
        );
      }
    } catch (err) {
      window.flashButton(btn, false);
      window.displayResult(
        "POST /move {direction: \"" + direction + "\", distance: 1}",
        { error: err.message || "Network error" },
        "move"
      );
    }
  });
});
