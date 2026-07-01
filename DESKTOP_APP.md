# Opening Omura like a desktop app

You have two ways to run Omura without juggling a browser. Both start the
backend + frontend for you.

## Option 1 — Desktop icon (recommended, easiest)

1. Double-click **`Create Omura Shortcut.bat`** once. This puts an **Omura**
   icon on your Desktop.
2. From now on, just double-click that **Omura** icon. It will:
   - start the backend (local SQLite API on port 8003),
   - start the frontend (port 3001),
   - wait until it's ready, then
   - open Omura in its **own app window** — no tabs, no address bar.

That's it. To quit, close the Omura window and the two minimized
"Omura Backend" / "Omura Frontend" windows in your taskbar.

> You can also just double-click **`Omura.bat`** directly — the shortcut simply
> runs it for you with a nicer icon.

## Option 2 — Install it from the browser (true PWA)

While Omura is open in Edge or Chrome:

- **Edge:** click the **⊕ / "Install this site as an app"** icon in the address
  bar (or menu → Apps → *Install this site as an app*).
- **Chrome:** menu → *Cast, save, and share* → **Install page as app…**

It gets its own Start-menu entry and taskbar icon and opens in a standalone
window, just like a native program.

## Notes

- First launch runs `npm install` once if dependencies aren't present — give it
  a minute. After that, startup is quick.
- The launcher uses Edge if installed, otherwise Chrome, otherwise your default
  browser.
- Ports: frontend `3001`, backend `8003` (matches `frontend/next.config.js` and
  `backend/serve_local.py`). If you change those, update `Omura.bat`.
