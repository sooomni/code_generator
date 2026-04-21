"""
Quick smoke tests — run with:  pytest test_cases.py -v
These hit the local FastAPI server (must be running on :8000).
"""
import pytest
import requests

BASE = "http://localhost:8000"


def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_generate_function():
    payload = {
        "function_name": "add_numbers",
        "description": "Add two integers and return the sum",
    }
    r = requests.post(f"{BASE}/generate/function", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "def add_numbers" in data["code"]
    assert data["validation"]["syntax_ok"] is True
    assert data["latency_ms"] < 10_000   # under 10 s


def test_generate_class():
    payload = {
        "class_name": "Calculator",
        "description": "Simple calculator with basic arithmetic",
        "methods": ["add", "subtract", "multiply", "divide"],
    }
    r = requests.post(f"{BASE}/generate/class", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "class Calculator" in data["code"]
    assert data["validation"]["syntax_ok"] is True


def test_generate_tests():
    source = (
        "def multiply(a: int, b: int) -> int:\n"
        '    """Return a * b."""\n'
        "    return a * b\n"
    )
    r = requests.post(f"{BASE}/generate/tests", json={"source_code": source})
    assert r.status_code == 200
    data = r.json()
    assert "def test_" in data["code"]


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


def test_validate_syntax_error():
    r = requests.post(f"{BASE}/validate", json={"code": "def broken(:\n    pass"})
    assert r.status_code == 200
    data = r.json()
    assert data["syntax_ok"] is False
    assert data["confidence_score"] == 0


def test_validate_security_issue():
    r = requests.post(f"{BASE}/validate", json={"code": "result = eval(user_input)"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["security_issues"]) > 0
    assert data["is_valid"] is False
