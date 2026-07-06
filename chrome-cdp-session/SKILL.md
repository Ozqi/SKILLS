---
name: chrome-cdp-session
description: Use the user's existing Chrome browser for DevTools-like work. Prefer standard Chrome DevTools Protocol when already available; otherwise inspect the current browser read-only with AppleScript and ask before restarting Chrome with a debugging port.
---

# Chrome CDP Session

Use this skill when a task needs browser inspection, DevTools/CDP access, or visibility into a logged-in web app such as Overleaf.

## Default Mode

Prefer the user's already-open Chrome browser.

1. Check whether the current Chrome exposes standard CDP:

```bash
curl -sS http://127.0.0.1:9222/json/version
curl -sS http://127.0.0.1:9222/json/list
```

Usable CDP returns JSON containing `Browser`, `Protocol-Version`, and `webSocketDebuggerUrl`.

Empty responses or `404` from `/json/version` mean the port is not standard CDP. On this user's macOS Chrome, `9222` may appear in `lsof` as `teamcoherence`; treat that as not usable for DevTools.

2. If CDP is unavailable, do not restart Chrome automatically. First inspect the existing browser read-only:

```bash
osascript -e 'tell application "Google Chrome"' \
  -e 'set out to ""' \
  -e 'repeat with w from 1 to count of windows' \
  -e 'repeat with t from 1 to count of tabs of window w' \
  -e 'set out to out & "window " & w & " tab " & t & " | " & title of tab t of window w & " | " & URL of tab t of window w & linefeed' \
  -e 'end repeat' \
  -e 'end repeat' \
  -e 'return out' \
  -e 'end tell'
```

This can confirm the current pages, titles, and URLs. It cannot inspect DOM, canvas, network requests, console logs, or PDF internals.

3. If the task truly needs DOM/network/PDF inspection, tell the user CDP is unavailable and ask before restarting Chrome with `--remote-debugging-port`.

## Restart With Real Profile

Only after user approval:

```bash
osascript -e 'tell application "Google Chrome" to quit'
open -a "Google Chrome" --args --remote-debugging-port=9222 --no-first-run --no-default-browser-check
```

Then verify:

```bash
curl -sS http://127.0.0.1:9222/json/version
curl -sS http://127.0.0.1:9222/json/list
```

Do not try to manually recreate the user's pages. Rely on Chrome session restore; the user can use `Cmd+Shift+T` or History if needed.

## Temporary Profiles

Do not use a temporary or copied profile by default. A temporary profile avoids touching the user's live browser, but it may lose login state or confuse future Chrome launches if left running.

Use a temporary/copy profile only when the user explicitly prefers that tradeoff. If used, shut it down before returning control to the user.

## Safety

- Ask for GUI escalation before `open` or `osascript`.
- Do not force kill Chrome unless the user explicitly allows it.
- Do not copy, print, or inspect cookies directly.
- If a copied profile was launched, stop it before reopening normal Chrome.
