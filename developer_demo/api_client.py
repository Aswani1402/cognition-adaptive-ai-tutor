import requests

from config import API_BASE_URL


ENDPOINTS = [
    ("GET", "/learner/context/{learner_id}"),
    ("POST", "/learner/select-subject"),
    ("GET", "/lesson/{concept_id}"),
    ("GET", "/assessment"),
    ("POST", "/assessment"),
    ("POST", "/answer/submit"),
    ("POST", "/code/run"),
    ("POST", "/doubt/ask"),
    ("GET", "/flashcards"),
    ("POST", "/flashcards"),
    ("GET", "/mindmap"),
    ("POST", "/mindmap"),
    ("GET", "/revision"),
    ("POST", "/revision"),
    ("GET", "/retention"),
    ("POST", "/retention"),
    ("GET", "/reward"),
    ("POST", "/reward"),
    ("GET", "/xai"),
    ("POST", "/xai"),
    ("GET", "/ai/evidence"),
    ("POST", "/ai/evidence"),
    ("GET", "/agentic/trace"),
    ("GET", "/generation/coverage"),
]


def request(method, path, learner_id=None, concept_id=None, payload=None, timeout=1.5):
    url = API_BASE_URL + path.format(learner_id=learner_id or 0, concept_id=concept_id or "P1")
    try:
        if method == "GET":
            res = requests.get(url, timeout=timeout)
        else:
            res = requests.post(url, json=payload or {}, timeout=timeout)
        if res.status_code < 400:
            try:
                body = res.json()
            except Exception:
                body = res.text[:300]
            return {"status": "PASS", "code": res.status_code, "url": url, "body": body}
        return {"status": "WARN", "code": res.status_code, "url": url, "body": "Endpoint returned non-success status."}
    except requests.exceptions.ConnectionError:
        return {"status": "NOT AVAILABLE", "code": None, "url": url, "body": "Backend is not reachable."}
    except Exception as exc:
        return {"status": "WARN", "code": None, "url": url, "body": str(exc)}


def backend_health():
    return request("GET", "/docs", timeout=1.0)


def endpoint_matrix(learner_id=None, concept_id=None, call_post=False):
    rows = []
    for method, path in ENDPOINTS:
        if method == "POST" and not call_post:
            rows.append({"method": method, "endpoint": path, "status": "WARN", "http": None, "connection": "Listed but not auto-called to avoid unintended write actions."})
            continue
        result = request(method, path, learner_id=learner_id, concept_id=concept_id)
        rows.append({"method": method, "endpoint": path, "status": result["status"], "http": result["code"], "connection": result["body"] if isinstance(result["body"], str) else "JSON response"})
    return rows
