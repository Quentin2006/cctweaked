const MOVE_ENDPOINT = "/move";

document.getElementById("up").addEventListener("click", () => {
  fetch(MOVE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction: "up", distance: 1 })
  });
});

document.getElementById("down").addEventListener("click", () => {
  fetch(MOVE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction: "down", distance: 1 })
  });
});

document.getElementById("forward").addEventListener("click", () => {
  fetch(MOVE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction: "forward", distance: 1 })
  });
});

document.getElementById("back").addEventListener("click", () => {
  fetch(MOVE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction: "back", distance: 1 })
  });
});

document.getElementById("left").addEventListener("click", () => {
  fetch(MOVE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction: "left", distance: 1 })
  });
});

document.getElementById("right").addEventListener("click", () => {
  fetch(MOVE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction: "right", distance: 1 })
  });
});
