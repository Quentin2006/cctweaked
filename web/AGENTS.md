# WEB — Frontend Dashboard

**Stack:** Vanilla HTML+CSS+JS / Three.js v0.160 (CDN via importmap)

## OVERVIEW

Single-page dashboard for turtle control — movement D-Pad, detect/inspect, dig/place/attack, inventory grid with drag-and-drop, 2×2 crafting, fuel gauge, and Three.js 3D world view. All CSS is inline (~1700 lines in `<style>`). Zero frameworks, zero build step.

## STRUCTURE

```
web/
├── index.html         # All HTML + CSS (~1700 lines style, ~100 lines inline JS)
├── move.js            # D-Pad → POST /move (41 lines)
├── detect.js          # Detect → POST /detect (41 lines)
├── action.js          # Dig/place/attack → POST /action + direction selector (66 lines)
├── inventory.js       # Inventory + crafting + drag-drop + fuel → GET/POST /inventory (225 lines, module)
├── visualize.js       # Three.js 3D scene — blocks + turtle (218 lines, module)
└── blocks.txt         # Persisted `x,y,z,name` CSV (may be empty)
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add new control button | `index.html` HTML + CSS | Follow `.dpad-btn`/`.action-btn` variant pattern |
| Add JS feature (global) | `move.js`/`detect.js`/`action.js` | Use `<script>` (not module), access `window.displayResult` |
| Add JS feature (module) | `inventory.js`/`visualize.js` | Use `<script type="module">`, no build step |
| Modify 3D rendering | `visualize.js` | Three.js ES module imports from CDN |
| Modify inventory logic | `inventory.js` | Polls every 2s, drag-and-drop via HTML5 Drag API |
| Change color theme | `index.html` `:root` | CSS custom properties — 6 accent colors, 3 fonts, spacing scale |
| Add new API call | any JS file | Follow the try/fetch/flashButton/displayResult pattern |

## CONVENTIONS

### Script loading order (index.html)
1. Inline `<script>` (defines `window.displayResult`, `window.flashButton`, `escapeHtml`, clock, connection check)
2. Classic `<script src="move.js">`
3. Classic `<script src="detect.js">`
4. Classic `<script src="action.js">`
5. `<script type="module" src="visualize.js">` (Three.js)
6. `<script type="module" src="inventory.js">` (inventory)

Classic scripts depend on `window.displayResult` and `window.flashButton` being defined by inline script.

### API call template (all non-module JS)
```javascript
const ENDPOINT = "/endpoint";
document.querySelectorAll("[data-attr]").forEach(btn => {
  btn.addEventListener("click", async () => {
    // GET param from dataset, POST, flashButton, displayResult
  });
});
```

### Naming
- JS vars/functions: `camelCase` (`displayResult`, `flashButton`, `fetchInventory`, `getItemColor`)
- Endpoint constants: `UPPER_SNAKE_CASE` (`MOVE_ENDPOINT`, `ACTION_ENDPOINT`)
- DO NOT use `var` — `move.js`/`detect.js`/`inventory.js`/`visualize.js` all use `const`
- Exception: `action.js` uses `var` — this is an inconsistency, use `const` for new code
- CSS classes: `kebab-case` (`.dpad-btn`, `.fuel-bar-fill`, `.log-entry`)
- CSS custom properties: `--kebab-case` (`--bg-deep`, `--font-display`, `--transition-bounce`)
- Data attributes: `data-direction`, `data-detect`, `data-action`, `data-dir`, `data-slot`

### Error handling
```javascript
} catch (_) {}  // AVOID — inventory.js has 3 silent catches
```
New code MUST log errors or show visual feedback. Do not replicate the silent catch pattern.

### CSS section format
```css
/* ===============================
   Section Name
   =============================== */
```

### Animation easings
- Interactive: `200ms cubic-bezier(0.34, 1.56, 0.64, 1)` (`--transition-bounce`)
- Hover/transitions: `300ms cubic-bezier(0.4, 0, 0.2, 1)` (`--transition-smooth`)
- ALWAYS include `@media (prefers-reduced-motion: reduce)` block

### Responsive breakpoints
- Desktop: >819px / Tablet: <=819px / Mobile: <=480px / Small: <=380px

## ANTI-PATTERNS (THIS DIRECTORY)

- **Empty catch blocks**: `inventory.js:100,194,221` and `visualize.js:144` silently swallow errors. `visualize.js:193` is tolerable (comment explains preserving last state).
- **var in action.js**: Only file using `var` instead of `const`. Do not replicate.
- **blocks.txt as flat-file DB**: CSV in a text file, no schema, no locking. Fine for small scale.
- **No health endpoint**: Connection check uses `POST /move` with `distance:0` as a hack.
