import os, json, base64, time, httpx
from email.mime.text import MIMEText
try:
    from google.oauth2 import credentials, service_account
    from google.auth.transport.requests import Request as AuthRequest
except ImportError:
    print(json.dumps({"error": "google-auth not installed. pip install google-auth"}))
    raise SystemExit(1)
try:
    inp = json.loads(os.environ.get("INPUT_JSON", "{}"))
    creds_json = json.loads(os.environ["GMAIL_CREDENTIALS_JSON"])
    user_email = os.environ.get("GMAIL_USER_EMAIL", "")
    if creds_json.get("type") == "authorized_user":
        creds = credentials.Credentials.from_authorized_user_info(
            creds_json, scopes=["https://www.googleapis.com/auth/gmail.send"]
        )
    else:
        creds = service_account.Credentials.from_service_account_info(
            creds_json, scopes=["https://www.googleapis.com/auth/gmail.send"], subject=user_email
        )
    creds.refresh(AuthRequest())
    msg = MIMEText(inp["body"])
    msg["to"] = inp["to"]
    msg["subject"] = inp["subject"]
    msg["from"] = user_email
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    for _attempt in range(4):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
                json={"raw": raw})
        if r.status_code == 429 and _attempt < 3:
            time.sleep(min(2 ** _attempt, 30))
            continue
        r.raise_for_status()
        break
    print(json.dumps({"ok": True, "message_id": r.json().get("id")}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
