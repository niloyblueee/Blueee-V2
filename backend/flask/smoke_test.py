import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:5000"


def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        return f"HTTP {err.code}: {body}"


def pretty_print(label, response_text):
    print(label)
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        print(response_text)
        return

    if isinstance(parsed, dict) and "summary" in parsed:
        print(parsed["summary"])
        return

    print(json.dumps(parsed, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    pretty_print(
        "/ai text test:",
        post("/ai", {"text": "Say hello from Blueee V2."})
    )

    pretty_print(
        "/ai tool call test (open_app notepad):",
        post("/ai", {"action": "open_app", "params": {"name": "notepad"}})
    )

    pretty_print(
        "/traffic test:",
        post("/traffic", {"origin": "Bogura", "destination": "Dhaka"})
    )
