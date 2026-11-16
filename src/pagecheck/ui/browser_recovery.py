"""Origin-scoped recovery token bridge for Streamlit >=1.56.

Unlike ?audit=TOKEN, a localStorage key never goes into URLs, browser history,
referrer headers or normal access logs. This is a bearer secret: XSS or a
shared browser profile can access it. No user-controlled JS is injected.
"""
from __future__ import annotations

from functools import lru_cache

# Trusted, static code only. Do not interpolate report content into this JS.
BRIDGE_JS = r"""
export default function(component) {
  const { data, setStateValue } = component;
  const key = 'pagecheck.recovery.v1';
  const valid = (v) => typeof v === 'string' && /^[A-Za-z0-9_-]{43}$/.test(v);
  let stored = null;
  try {
    if (data?.command === 'clear') {
      localStorage.removeItem(key);
    } else if (data?.command === 'set' && valid(data.token)) {
      localStorage.setItem(key, data.token);
    }
    stored = localStorage.getItem(key);
    if (stored && !valid(stored)) {
      localStorage.removeItem(key);
      stored = null;
    }
  } catch (_) { stored = null; }
  // A 'set' or 'clear' command must also update the component state;
  // otherwise a previous audit's token could be replayed on a later rerun.
  if (data?.command === 'set' || data?.command === 'clear' ||
      stored !== (data?.known_token || null)) {
    setStateValue('token', stored);
  }
}
"""


@lru_cache(maxsize=1)
def _component():
    import streamlit as st
    if not hasattr(st.components, "v2"):
        raise RuntimeError("Streamlit >=1.56 is required for browser recovery.")
    return st.components.v2.component("pagecheck.recovery", js=BRIDGE_JS)


def browser_recovery(*, known_token: str | None, set_token: str | None = None,
                     clear: bool = False) -> str | None:
    """Read/write a single browser token without query params.

    The component reports state asynchronously; after F5 it triggers one
    Streamlit rerun as soon as localStorage is ready.
    """
    if clear:
        command = "clear"
    elif set_token:
        command = "set"
    else:
        command = "read"
    result = _component()(
        key="pagecheck_recovery_store",
        data={"command": command, "token": set_token, "known_token": known_token},
        on_token_change=lambda: None,
    )
    value = getattr(result, "token", None)
    return value if isinstance(value, str) and len(value) == 43 else None
