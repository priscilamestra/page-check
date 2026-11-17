"""Opt-in browser inactivity pause for Streamlit on Render Free.

No server polling or keep-alive. After an inactivity window this navigates to a
self-contained in-browser page, unloading Streamlit and closing its WebSocket.
Returning starts a new session; the existing browser-local Neon recovery token
allows restoring recent reports. This intentionally does not touch local dev.
"""
from __future__ import annotations

import os

import streamlit as st


def idle_guard_enabled(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return (env.get("PAGECHECK_ENV", "local").strip().lower() == "production"
            and env.get("PAGECHECK_UI_IDLE_GUARD") == "1")


def idle_minutes(environ: dict[str, str] | None = None) -> int:
    env = os.environ if environ is None else environ
    try:
        minutes = int(env.get("PAGECHECK_UI_IDLE_MINUTES", "15"))
    except (TypeError, ValueError):
        return 15
    return max(10, min(60, minutes))


def idle_guard_html(minutes: int) -> str:
    """Return fixed-source JS with a bounded integer timeout (no user content)."""
    millis = max(10, min(60, int(minutes))) * 60_000
    return r'''<script>
(() => {
  'use strict';
  const KEY = '__pagecheck_render_free_idle_guard_v1';
  const idleMs = __IDLE_MS__;
  if (window[KEY]) return; // Streamlit reruns must not add duplicate timers.
  let lastActivity = Date.now();
  let paused = false;
  const home = window.location.origin + window.location.pathname;
  function pauseWhenIdle() {
    if (paused || Date.now() - lastActivity < idleMs) return;
    paused = true;
    // Navigating to an in-memory document unloads the Streamlit WebSocket.
    // The paused document does not poll, ping, or request a backend resource.
    const safeHome = home.replaceAll('&', '&amp;').replaceAll('"', '&quot;')
      .replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    const page = `<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page Check — Session paused</title>
<style>
body{font:16px system-ui,sans-serif;margin:0;min-height:100vh;display:grid;
place-items:center;background:#fafafa;color:#232323}
main{max-width:420px;padding:32px;text-align:center}
a{display:inline-block;margin-top:12px;padding:12px 22px;border-radius:8px;
background:#202020;color:white;text-decoration:none}
</style><main><h1>Session paused</h1>
<p>This inactive tab was paused to save free hosting hours.
You can return anytime. Recent reports may be recovered for up to 24 hours.</p>
<a href="${safeHome}">Return to Page Check</a></main></html>`;
    const idleUrl = URL.createObjectURL(new Blob([page], {type: 'text/html'}));
    window.location.replace(idleUrl);
  }
  function active() { lastActivity = Date.now(); }
  for (const name of ['pointerdown', 'keydown', 'mousemove', 'wheel',
                       'touchstart', 'scroll']) {
    document.addEventListener(name, active, {passive: true, capture: true});
  }
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) pauseWhenIdle();
  }, {passive: true});
  // Local browser timer only. When background-throttled, pausing may be late.
  const timer = window.setInterval(pauseWhenIdle, 30_000);
  window[KEY] = {timer};
})();
</script>'''.replace("__IDLE_MS__", str(millis))


def enable_idle_guard() -> None:
    if idle_guard_enabled():
        st.html(idle_guard_html(idle_minutes()), unsafe_allow_javascript=True)
