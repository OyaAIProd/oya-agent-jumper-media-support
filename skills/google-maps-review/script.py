"""
Google Maps Review — navigates to a place, selects stars, types review, posts it.

Uses the AgentChrome REST API: GET /api/pool + POST /api/browsers/{id}/command.
Pins to one browser for the entire session.
"""
import json
import os
import re
import time

import httpx

API_KEY = os.environ.get("BROWSER_API_KEY", "")
API_BASE = os.environ.get("BROWSER_API_BASE", "https://browser.oya.ai").rstrip("/")
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


# ─── Low-level helpers ───


CLIENT = httpx.Client(timeout=60, headers=HEADERS)


_resolve_error = ""

def resolve_browser() -> str:
    """Pick first browser from pool. Retries up to 3 times with 2s pause."""
    global _resolve_error
    for attempt in range(3):
        try:
            r = CLIENT.get(f"{API_BASE}/api/pool", timeout=10)
            _resolve_error = f"pool status={r.status_code} body={r.text[:200]}"
            if r.status_code == 200:
                browsers = r.json().get("browsers", [])
                if browsers:
                    return browsers[0]["id"]
                _resolve_error = f"pool returned 0 browsers (key={API_KEY[:8]}...)"
        except Exception as e:
            _resolve_error = f"pool request failed: {e} (base={API_BASE})"
        if attempt < 2:
            time.sleep(2)
    return ""


def cmd(bid: str, action: str, params: dict | None = None, timeout: int = 35) -> dict:
    """Send a command to a specific browser. Retries once on 404 (browser reconnecting)."""
    for attempt in range(2):
        try:
            r = CLIENT.post(
                f"{API_BASE}/api/browsers/{bid}/command",
                json={"action": action, "params": params or {}},
                timeout=timeout,
            )
            if r.status_code == 404 and attempt == 0:
                time.sleep(2)
                continue
            try:
                return r.json()
            except Exception:
                return {"ok": False, "error": f"Non-JSON response ({r.status_code}): {r.text[:200]}"}
        except httpx.TimeoutException:
            return {"ok": False, "error": f"{action} timed out after {timeout}s"}
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
                continue
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "command failed after retries"}


def sel(eid: int) -> str:
    return f'[data-ac-id="{eid}"]'


def do_analyze(bid: str) -> tuple[str, list[dict]]:
    """Analyze page, return (markdown, elements). Retries once if empty."""
    for attempt in range(2):
        result = cmd(bid, "analyze", timeout=45)
        if result.get("ok"):
            data = result.get("data", {})
            md = data.get("markdown", "")
            els = data.get("elements", [])
            if md or els:
                return md, els
        if attempt == 0:
            time.sleep(2)
    return "", []


def find_eid(elements: list[dict], *keywords: str) -> int | None:
    """Find first element whose text/type/label matches ALL keywords (case-insensitive)."""
    lower_kw = [k.lower() for k in keywords]
    for el in elements:
        blob = " ".join(str(v) for v in [el.get("type", ""), el.get("text", ""), el.get("ariaLabel", ""), el.get("placeholder", "")]).lower()
        if all(k in blob for k in lower_kw):
            return el.get("id")
    return None


def find_all_eids(elements: list[dict], *keywords: str) -> list[int]:
    """Find ALL element IDs matching keywords."""
    lower_kw = [k.lower() for k in keywords]
    results = []
    for el in elements:
        blob = " ".join(str(v) for v in [el.get("type", ""), el.get("text", ""), el.get("ariaLabel", ""), el.get("placeholder", "")]).lower()
        if all(k in blob for k in lower_kw):
            eid = el.get("id")
            if eid is not None:
                results.append(eid)
    return results


def fail(msg: str):
    print(json.dumps({"error": msg}))
    raise SystemExit(0)


def ok(msg: str, **extra):
    print(json.dumps({"ok": True, "message": msg, **extra}))
    raise SystemExit(0)


# ─── Steps ───


def step_navigate(bid: str, place: str) -> tuple[str, list[dict]]:
    """Navigate to Google Maps place page. Returns (markdown, elements)."""
    if place.startswith("http"):
        url = place
    else:
        url = f"https://www.google.com/maps/search/{place.replace(' ', '+')}"

    result = cmd(bid, "navigate", {"url": url}, timeout=90)
    # Even if navigate "fails" (timeout), the page may have loaded
    time.sleep(3)
    md, els = do_analyze(bid)
    if not md:
        return "", []

    # If we're on search results (multiple places), click the first result
    if "write a review" not in md.lower():
        # Try clicking first place link
        first_place = find_eid(els, "link")
        if first_place:
            cmd(bid, "click", {"selector": sel(first_place)})
            time.sleep(3)
            md, els = do_analyze(bid)

    return md, els


def step_find_write_review(bid: str, md: str, els: list[dict]) -> tuple[str, list[dict]]:
    """Find and click 'Write a review'. Returns (markdown, elements) of review dialog."""
    eid = find_eid(els, "write a review") or find_eid(els, "write", "review")

    if not eid:
        # Scroll down — button might be below fold
        for _ in range(3):
            cmd(bid, "scroll", {"direction": "down", "amount": 600})
            time.sleep(1)
            md, els = do_analyze(bid)
            eid = find_eid(els, "write a review") or find_eid(els, "write", "review")
            if eid:
                break

    if not eid:
        return "", []

    cmd(bid, "click", {"selector": sel(eid)})
    time.sleep(2)
    md, els = do_analyze(bid)
    return md, els


def step_select_stars(bid: str, els: list[dict], stars: int) -> tuple[str, list[dict]]:
    """Click the star rating."""
    # Try aria-label pattern: "1 star", "2 stars", etc.
    label = f"{stars} star"
    eid = find_eid(els, label)
    if eid:
        cmd(bid, "click", {"selector": sel(eid)})
        time.sleep(1)
        return do_analyze(bid)

    # Fallback: find all star elements and click the Nth
    star_ids = find_all_eids(els, "star")
    if len(star_ids) >= stars:
        cmd(bid, "click", {"selector": sel(star_ids[stars - 1])})
        time.sleep(1)
        return do_analyze(bid)

    return "", els


def step_type_review(bid: str, els: list[dict], text: str) -> tuple[str, list[dict]]:
    """Type the review text."""
    eid = (
        find_eid(els, "textarea")
        or find_eid(els, "share details")
        or find_eid(els, "your experience")
        or find_eid(els, "review")
    )

    if not eid:
        # Scroll within dialog
        cmd(bid, "scroll", {"direction": "down", "amount": 300})
        time.sleep(1)
        _, els = do_analyze(bid)
        eid = find_eid(els, "textarea") or find_eid(els, "share details")

    if not eid:
        return "", els

    # Click to focus, then type
    cmd(bid, "click", {"selector": sel(eid)})
    time.sleep(0.5)
    cmd(bid, "type", {"selector": sel(eid), "text": text})
    time.sleep(1)
    return do_analyze(bid)


def step_post(bid: str, els: list[dict]) -> bool:
    """Click the Post button."""
    eid = find_eid(els, "post") or find_eid(els, "submit") or find_eid(els, "publish")
    if not eid:
        return False
    result = cmd(bid, "click", {"selector": sel(eid)})
    return result.get("ok", False)


# ─── Main ───

try:
    if not API_KEY:
        fail(f"BROWSER_API_KEY not set — connect a browser gateway first (API_BASE={API_BASE})")

    # Debug: verify connectivity
    import sys
    print(f"[debug] API_BASE={API_BASE} API_KEY={API_KEY[:8]}... ", file=sys.stderr)

    inp = json.loads(os.environ.get("INPUT_JSON", "{}"))
    place = inp.get("place", "").strip()
    stars = int(inp.get("stars", 5))
    review_text = inp.get("review_text", "").strip()

    if not place:
        fail("place is required — provide a Google Maps URL or place name")
    if not review_text:
        fail("review_text is required")
    if stars < 1 or stars > 5:
        fail("stars must be between 1 and 5")

    bid = resolve_browser()
    if not bid:
        fail(f"No browsers connected — {_resolve_error}")

    # Step 1: Navigate to place
    md, els = step_navigate(bid, place)
    if not md:
        fail(f"Failed to load Google Maps page for: {place}")

    # Step 2: Click "Write a review"
    md, els = step_find_write_review(bid, md, els)
    if not md:
        fail("Could not find 'Write a review' button — make sure the browser is logged into Google")

    # Step 3: Select stars
    md, els = step_select_stars(bid, els, stars)

    # Step 4: Type review
    md, els = step_type_review(bid, els, review_text)

    # Step 5: Post
    posted = step_post(bid, els)
    if not posted:
        # Re-analyze and retry
        _, els = do_analyze(bid)
        posted = step_post(bid, els)

    if posted:
        time.sleep(2)
        ok(f"Posted {stars}-star review on {place}", review_text=review_text)
    else:
        fail("Could not find the Post button. The review was typed but may not have been submitted — check the browser.")

except SystemExit:
    pass
except Exception as e:
    print(json.dumps({"error": str(e)}))
finally:
    CLIENT.close()
