const DETECT_ENDPOINT = "/detect";

document.getElementById("detect").addEventListener("click", async () => {
  let resp = await fetch(DETECT_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction: "forward" })
  });
  console.log(await resp.json());
});

document.getElementById("detect_up").addEventListener("click", async () => {
  let resp = await fetch(DETECT_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction: "up" })
  });
  console.log(await resp.json());
});

document.getElementById("detect_down").addEventListener("click", async () => {
  let resp = await fetch(DETECT_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction: "down" })
  });
  console.log(await resp.json());
});
