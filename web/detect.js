const DETECT_ENDPOINT = "/detect";

document.querySelectorAll("[data-detect]").forEach(function (btn) {
  btn.addEventListener("click", async function () {
    const direction = btn.getAttribute("data-detect");
    const body = JSON.stringify({ direction: direction });

    try {
      const resp = await fetch(DETECT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
      });

      const result = await resp.json();

      if (resp.ok) {
        window.flashButton(btn, true);
        window.displayResult(
          "POST /detect {direction: \"" + direction + "\"}",
          result,
          "detect"
        );
      } else {
        window.flashButton(btn, false);
        window.displayResult(
          "POST /detect {direction: \"" + direction + "\"}",
          { error: result.error || "HTTP " + resp.status },
          "detect"
        );
      }
    } catch (err) {
      window.flashButton(btn, false);
      window.displayResult(
        "POST /detect {direction: \"" + direction + "\"}",
        { error: err.message || "Network error" },
        "detect"
      );
    }
  });
});
