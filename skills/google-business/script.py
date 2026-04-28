import os
import json
import time
import httpx

try:
    from google.oauth2 import credentials, service_account
    from google.auth.transport.requests import Request as AuthRequest
except ImportError:
    print(json.dumps({"error": "google-auth not installed. pip install google-auth"}))
    raise SystemExit(1)

ACCOUNT_API = "https://mybusinessaccountmanagement.googleapis.com/v1"
LOCATION_API = "https://mybusinessbusinessinformation.googleapis.com/v1"
LEGACY_API = "https://mybusiness.googleapis.com/v4"
SCOPES = [
    "https://www.googleapis.com/auth/business.manage",
]
MAX_RETRIES = 4
DELAY = 0.05


def get_creds(creds_json):
    if creds_json.get("type") == "authorized_user":
        creds = credentials.Credentials.from_authorized_user_info(creds_json, scopes=SCOPES)
    else:
        creds = service_account.Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    creds.refresh(AuthRequest())
    return creds


def _headers(creds):
    return {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}


def _api(method, url, creds, timeout=15, **kwargs):
    """HTTP request with exponential backoff on 429."""
    time.sleep(DELAY)
    for attempt in range(MAX_RETRIES + 1):
        with httpx.Client(timeout=timeout) as c:
            r = c.request(method, url, headers=_headers(creds), **kwargs)
        if r.status_code == 429 and attempt < MAX_RETRIES:
            time.sleep(min(2 ** attempt, 30))
            continue
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text[:500]
            raise Exception(f"HTTP {r.status_code}: {json.dumps(detail) if isinstance(detail, dict) else detail}")
        return r.json()


def do_list_accounts(creds):
    data = _api("GET", f"{ACCOUNT_API}/accounts", creds)
    accounts = data.get("accounts", [])
    return {
        "accounts": [
            {
                "name": a.get("name", ""),
                "account_name": a.get("accountName", ""),
                "type": a.get("type", ""),
                "role": a.get("role", ""),
            }
            for a in accounts
        ],
        "count": len(accounts),
    }


def do_list_locations(creds, account_id):
    data = _api("GET", f"{LOCATION_API}/accounts/{account_id}/locations", creds,
                params={"readMask": "name,title,storefrontAddress,websiteUri,phoneNumbers"})
    locations = data.get("locations", [])
    return {
        "locations": [
            {
                "name": loc.get("name", ""),
                "title": loc.get("title", ""),
                "address": loc.get("storefrontAddress", {}),
                "website": loc.get("websiteUri", ""),
                "phone": loc.get("phoneNumbers", {}).get("primaryPhone", ""),
            }
            for loc in locations
        ],
        "count": len(locations),
    }


def do_get_location(creds, location_id):
    data = _api("GET", f"{LOCATION_API}/locations/{location_id}", creds,
                params={"readMask": "name,title,storefrontAddress,websiteUri,phoneNumbers,categories,profile,metadata"})
    return {
        "name": data.get("name", ""),
        "title": data.get("title", ""),
        "address": data.get("storefrontAddress", {}),
        "website": data.get("websiteUri", ""),
        "phone": data.get("phoneNumbers", {}).get("primaryPhone", ""),
        "categories": data.get("categories", {}),
        "profile": data.get("profile", {}),
        "metadata": data.get("metadata", {}),
    }


def do_list_reviews(creds, account_id, location_id):
    data = _api("GET", f"{LEGACY_API}/accounts/{account_id}/locations/{location_id}/reviews", creds)
    reviews = data.get("reviews", [])
    return {
        "reviews": [
            {
                "name": r.get("name", ""),
                "review_id": r.get("reviewId", ""),
                "reviewer": r.get("reviewer", {}).get("displayName", ""),
                "star_rating": r.get("starRating", ""),
                "comment": r.get("comment", ""),
                "create_time": r.get("createTime", ""),
                "update_time": r.get("updateTime", ""),
                "reply": r.get("reviewReply", {}).get("comment", "") if r.get("reviewReply") else "",
            }
            for r in reviews
        ],
        "count": len(reviews),
        "average_rating": data.get("averageRating", 0),
        "total_review_count": data.get("totalReviewCount", 0),
    }


def do_reply_to_review(creds, account_id, location_id, review_id, reply_text):
    body = {"comment": reply_text}
    data = _api("PUT",
                f"{LEGACY_API}/accounts/{account_id}/locations/{location_id}/reviews/{review_id}/reply",
                creds, json=body)
    return {
        "comment": data.get("comment", ""),
        "update_time": data.get("updateTime", ""),
    }


def do_create_post(creds, account_id, location_id, post_body, media_url, cta_type, cta_url):
    body = {
        "languageCode": "en",
        "summary": post_body,
        "topicType": "STANDARD",
    }
    if media_url:
        body["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": media_url}]
    if cta_type and cta_url:
        body["callToAction"] = {"actionType": cta_type, "url": cta_url}
    data = _api("POST",
                f"{LEGACY_API}/accounts/{account_id}/locations/{location_id}/localPosts",
                creds, json=body)
    return {
        "name": data.get("name", ""),
        "summary": data.get("summary", ""),
        "state": data.get("state", ""),
        "create_time": data.get("createTime", ""),
        "update_time": data.get("updateTime", ""),
        "topic_type": data.get("topicType", ""),
        "search_url": data.get("searchUrl", ""),
    }


def do_list_posts(creds, account_id, location_id):
    data = _api("GET",
                f"{LEGACY_API}/accounts/{account_id}/locations/{location_id}/localPosts",
                creds)
    posts = data.get("localPosts", [])
    return {
        "posts": [
            {
                "name": p.get("name", ""),
                "summary": p.get("summary", ""),
                "state": p.get("state", ""),
                "topic_type": p.get("topicType", ""),
                "create_time": p.get("createTime", ""),
                "update_time": p.get("updateTime", ""),
                "search_url": p.get("searchUrl", ""),
            }
            for p in posts
        ],
        "count": len(posts),
    }


def do_get_insights(creds, account_id, location_id, start_date, end_date, metric_requests):
    metrics = [m.strip() for m in metric_requests.split(",") if m.strip()]
    body = {
        "locationNames": [f"accounts/{account_id}/locations/{location_id}"],
        "basicRequest": {
            "metricRequests": [{"metric": m} for m in metrics],
            "timeRange": {
                "startTime": f"{start_date}T00:00:00Z",
                "endTime": f"{end_date}T23:59:59Z",
            },
        },
    }
    data = _api("POST",
                f"{LEGACY_API}/accounts/{account_id}/locations:reportInsights",
                creds, json=body, timeout=30)
    reports = data.get("locationMetrics", [])
    if reports:
        report = reports[0]
        metric_values = report.get("metricValues", [])
        return {
            "location": report.get("locationName", ""),
            "time_zone": report.get("timeZone", ""),
            "metrics": [
                {
                    "metric": mv.get("metric", ""),
                    "total_value": mv.get("totalValue", {}).get("metricValue", 0),
                    "dimensional_values": mv.get("dimensionalValues", []),
                }
                for mv in metric_values
            ],
        }
    return {"location": "", "metrics": [], "message": "No insights data returned"}


try:
    creds_json = json.loads(os.environ["GOOGLE_BUSINESS_CREDENTIALS_JSON"])
    creds = get_creds(creds_json)
    inp = json.loads(os.environ.get("INPUT_JSON", "{}"))
    action = inp.get("action", "")

    if action == "list_accounts":
        result = do_list_accounts(creds)
    elif action == "list_locations":
        result = do_list_locations(creds, inp.get("account_id", ""))
    elif action == "get_location":
        result = do_get_location(creds, inp.get("location_id", ""))
    elif action == "list_reviews":
        result = do_list_reviews(creds, inp.get("account_id", ""), inp.get("location_id", ""))
    elif action == "reply_to_review":
        result = do_reply_to_review(creds, inp.get("account_id", ""), inp.get("location_id", ""),
                                     inp.get("review_id", ""), inp.get("reply_text", ""))
    elif action == "create_post":
        result = do_create_post(creds, inp.get("account_id", ""), inp.get("location_id", ""),
                                 inp.get("post_body", ""), inp.get("post_media_url", ""),
                                 inp.get("post_call_to_action_type", ""), inp.get("post_call_to_action_url", ""))
    elif action == "list_posts":
        result = do_list_posts(creds, inp.get("account_id", ""), inp.get("location_id", ""))
    elif action == "get_insights":
        result = do_get_insights(
            creds, inp.get("account_id", ""), inp.get("location_id", ""),
            inp.get("start_date", ""), inp.get("end_date", ""),
            inp.get("metric_requests",
                     "QUERIES_DIRECT,QUERIES_INDIRECT,VIEWS_MAPS,VIEWS_SEARCH,ACTIONS_WEBSITE,ACTIONS_PHONE,ACTIONS_DRIVING_DIRECTIONS"),
        )
    else:
        result = {"error": f"Unknown action: {action}"}

    print(json.dumps(result))

except Exception as e:
    print(json.dumps({"error": str(e)}))
