"""
Integration tests — FastAPI server must be running on :8000.
Run with:  pytest test_cases.py -v

Start server first:  python main.py
"""
import pytest
import requests

BASE = "http://localhost:8000"


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def require_server():
    try:
        r = requests.get(f"{BASE}/health", timeout=3)
        r.raise_for_status()
    except Exception:
        pytest.skip("FastAPI server not running — skipping integration tests")


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "supported_models" in data
    assert "default_model" in data


def test_health_supported_models_keys():
    data = requests.get(f"{BASE}/health").json()
    for key in ("granite-8b", "llama-70b", "mistral-small"):
        assert key in data["supported_models"]


# ── /generate/function ────────────────────────────────────────────────────────

def test_generate_function_default_model():
    payload = {
        "function_name": "add_numbers",
        "description": "Add two integers and return the sum",
    }
    r = requests.post(f"{BASE}/generate/function", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "def add_numbers" in data["code"]
    assert data["validation"]["syntax_ok"] is True
    assert data["latency_ms"] < 30_000
    assert data["model_id"] != ""


def test_generate_function_model_selection():
    payload = {
        "function_name": "greet",
        "description": "Return a greeting string",
        "model": "granite-8b",
    }
    r = requests.post(f"{BASE}/generate/function", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "ibm/granite-8b-code-instruct" in data["model_id"]


def test_generate_function_response_shape():
    payload = {"function_name": "noop", "description": "Do nothing"}
    data = requests.post(f"{BASE}/generate/function", json=payload).json()
    for key in ("code", "validation", "latency_ms", "tokens_used", "confidence_score", "model_id", "timestamp"):
        assert key in data, f"Missing key: {key}"
    for vkey in ("syntax_ok", "is_valid", "security_issues", "security_details", "risk_level", "quality_score", "quality_notes"):
        assert vkey in data["validation"], f"Missing validation key: {vkey}"


# ── /generate/class ───────────────────────────────────────────────────────────

def test_generate_class():
    payload = {
        "class_name": "Calculator",
        "description": "Simple calculator with basic arithmetic",
        "methods": ["add", "subtract"],
    }
    r = requests.post(f"{BASE}/generate/class", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "class Calculator" in data["code"]
    assert data["validation"]["syntax_ok"] is True


# ── /generate/tests ───────────────────────────────────────────────────────────

def test_generate_tests():
    source = (
        "def multiply(a: int, b: int) -> int:\n"
        '    """Return a * b."""\n'
        "    return a * b\n"
    )
    r = requests.post(f"{BASE}/generate/tests", json={"source_code": source})
    assert r.status_code == 200
    assert "def test_" in r.json()["code"]


# ── /validate ─────────────────────────────────────────────────────────────────

def test_validate_valid_code():
    code = (
        "def greet(name: str) -> str:\n"
        '    """Return a greeting."""\n'
        '    return f"Hello, {name}!"\n'
    )
    r = requests.post(f"{BASE}/validate", json={"code": code})
    assert r.status_code == 200
    data = r.json()
    assert data["syntax_ok"] is True
    assert data["is_valid"] is True
    assert data["confidence_score"] == 100
    assert data["security_issues"] == []
    assert data["risk_level"] is None


def test_validate_syntax_error():
    r = requests.post(f"{BASE}/validate", json={"code": "def broken(:\n    pass"})
    assert r.status_code == 200
    data = r.json()
    assert data["syntax_ok"] is False
    assert data["confidence_score"] == 0


def test_validate_security_eval_critical():
    r = requests.post(f"{BASE}/validate", json={"code": "result = eval(user_input)"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["security_issues"]) > 0
    assert data["is_valid"] is False
    # severity fields
    assert data["risk_level"] == "CRITICAL"
    details = data["security_details"]
    assert any(d["severity"] == "CRITICAL" for d in details)


def test_validate_security_weak_hash_medium():
    r = requests.post(f"{BASE}/validate", json={"code": "import hashlib\nhashlib.md5(b'pw')"})
    assert r.status_code == 200
    data = r.json()
    assert data["risk_level"] == "MEDIUM"
    assert any(d["label"] == "weak hashing algorithm" for d in data["security_details"])


def test_validate_security_details_structure():
    r = requests.post(f"{BASE}/validate", json={"code": "eval(x)"})
    data = r.json()
    for detail in data["security_details"]:
        assert "label" in detail
        assert "severity" in detail
        assert detail["severity"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")


# ── /stats ────────────────────────────────────────────────────────────────────

def test_stats_shape():
    r = requests.get(f"{BASE}/stats")
    assert r.status_code == 200
    data = r.json()
    for key in ("total", "today", "projection", "by_model", "by_type", "daily_trend", "pricing"):
        assert key in data, f"Missing stats key: {key}"


def test_stats_total_fields():
    data = requests.get(f"{BASE}/stats").json()
    total = data["total"]
    for key in ("calls", "input_tokens", "output_tokens", "total_tokens", "cost_usd"):
        assert key in total


def test_stats_projection_fields():
    data = requests.get(f"{BASE}/stats").json()
    proj = data["projection"]
    for key in ("avg_daily_cost_usd", "projected_monthly_usd", "active_days"):
        assert key in proj


def test_stats_pricing_contains_all_models():
    data = requests.get(f"{BASE}/stats").json()
    pricing = data["pricing"]
    for model_id in (
        "ibm/granite-8b-code-instruct",
        "meta-llama/llama-3-3-70b-instruct",
        "mistralai/mistral-small-3-1-24b-instruct-2503",
    ):
        assert model_id in pricing
