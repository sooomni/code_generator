"""
Unit tests — no server required.
Run with:  pytest test_unit.py -v
"""
import json
import tempfile
from pathlib import Path

import pytest

from code_validator import validate, DANGEROUS_PATTERNS, SeverityLevel


# ── code_validator: syntax ────────────────────────────────────────────────────

def test_syntax_valid():
    result = validate("x = 1 + 2")
    assert result.syntax_ok is True
    assert result.error is None


def test_syntax_error():
    result = validate("def broken(:\n    pass")
    assert result.syntax_ok is False
    assert result.confidence_score == 0
    assert "SyntaxError" in result.error


def test_empty_code():
    result = validate("")
    assert result.syntax_ok is True
    assert result.quality_score == 100


# ── code_validator: security patterns ────────────────────────────────────────

CRITICAL_CASES = [
    ("result = eval(x)",          "eval() usage"),
    ("exec('import os')",         "exec() usage"),
    ("__import__('os')",          "__import__() usage"),
    ("subprocess.run(cmd, shell=True)", "subprocess shell=True"),
    ("os.system('ls')",           "os.system() usage"),
]

HIGH_CASES = [
    ("pickle.loads(data)",        "pickle deserialization"),
    ("yaml.load(f)",              "yaml.load() without Loader"),
]

MEDIUM_CASES = [
    ("hashlib.md5(b'pw')",        "weak hashing algorithm"),
    ("hashlib.sha1(b'pw')",       "weak hashing algorithm"),
]

LOW_CASES = [
    ("open('out.txt', 'w')",      "file write operation"),
]


@pytest.mark.parametrize("code,label", CRITICAL_CASES)
def test_critical_pattern(code, label):
    result = validate(code)
    matched = [d for d in result.security_details if d.label == label]
    assert matched, f"Expected '{label}' to be detected"
    assert matched[0].severity == "CRITICAL"
    assert result.risk_level == "CRITICAL"


@pytest.mark.parametrize("code,label", HIGH_CASES)
def test_high_pattern(code, label):
    result = validate(code)
    matched = [d for d in result.security_details if d.label == label]
    assert matched, f"Expected '{label}' to be detected"
    assert matched[0].severity == "HIGH"


@pytest.mark.parametrize("code,label", MEDIUM_CASES)
def test_medium_pattern(code, label):
    result = validate(code)
    matched = [d for d in result.security_details if d.label == label]
    assert matched, f"Expected '{label}' to be detected"
    assert matched[0].severity == "MEDIUM"


@pytest.mark.parametrize("code,label", LOW_CASES)
def test_low_pattern(code, label):
    result = validate(code)
    matched = [d for d in result.security_details if d.label == label]
    assert matched, f"Expected '{label}' to be detected"
    assert matched[0].severity == "LOW"


def test_no_false_positive_safe_code():
    code = (
        "def greet(name: str) -> str:\n"
        '    """Return a greeting."""\n'
        '    return f"Hello, {name}!"\n'
    )
    result = validate(code)
    assert result.security_issues == []
    assert result.risk_level is None
    assert result.is_valid is True


def test_multiple_issues_risk_level_is_worst():
    code = "hashlib.md5(b'x')\nopen('f', 'w')"
    result = validate(code)
    assert result.risk_level == "MEDIUM"  # md5=MEDIUM > file write=LOW


def test_critical_dominates_lower_severity():
    code = "eval(x)\nhashlib.md5(b'x')"
    result = validate(code)
    assert result.risk_level == "CRITICAL"


# ── code_validator: quality score ────────────────────────────────────────────

def test_quality_full_score():
    code = (
        "def add(a: int, b: int) -> int:\n"
        '    """Return a + b."""\n'
        "    return a + b\n"
    )
    result = validate(code)
    assert result.quality_score == 100


def test_quality_missing_docstring():
    code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    result = validate(code)
    # has type hints but no docstring → -15 only
    assert result.quality_score == 85
    assert any("docstring" in n.lower() for n in result.quality_notes)


def test_quality_missing_type_hints():
    code = (
        "def add(a, b):\n"
        '    """Return a + b."""\n'
        "    return a + b\n"
    )
    result = validate(code)
    assert any("type hints" in n.lower() for n in result.quality_notes)


def test_confidence_penalised_by_severity():
    # CRITICAL penalty = 30 → confidence = quality - 30
    code = (
        "def bad(a: int, b: int) -> int:\n"
        '    """Do something."""\n'
        "    return eval(a)\n"
    )
    result = validate(code)
    assert result.quality_score == 100
    assert result.confidence_score == 70  # 100 - 30


# ── token_tracker: unit tests ────────────────────────────────────────────────

def test_load_stats_empty(tmp_path, monkeypatch):
    import token_tracker
    monkeypatch.setattr(token_tracker, "LOG_PATH", tmp_path / "empty.jsonl")
    stats = token_tracker.load_stats()
    assert stats["total"]["calls"] == 0
    assert stats["total"]["cost_usd"] == 0.0
    assert stats["by_model"] == {}


def test_load_stats_single_record(tmp_path, monkeypatch):
    import token_tracker
    log = tmp_path / "gen.jsonl"
    record = {
        "timestamp": "2026-04-22T10:00:00",
        "type": "function",
        "model_id": "ibm/granite-8b-code-instruct",
        "input_tokens": 100,
        "output_tokens": 50,
    }
    log.write_text(json.dumps(record) + "\n", encoding="utf-8")
    monkeypatch.setattr(token_tracker, "LOG_PATH", log)

    stats = token_tracker.load_stats()
    assert stats["total"]["calls"] == 1
    assert stats["total"]["input_tokens"] == 100
    assert stats["total"]["output_tokens"] == 50
    assert stats["by_type"]["function"] == 1
    assert "ibm/granite-8b-code-instruct" in stats["by_model"]


def test_load_stats_cost_calculation(tmp_path, monkeypatch):
    import token_tracker
    log = tmp_path / "gen.jsonl"
    record = {
        "timestamp": "2026-04-22T10:00:00",
        "type": "function",
        "model_id": "ibm/granite-8b-code-instruct",
        "input_tokens": 1000,
        "output_tokens": 1000,
    }
    log.write_text(json.dumps(record) + "\n", encoding="utf-8")
    monkeypatch.setattr(token_tracker, "LOG_PATH", log)

    stats = token_tracker.load_stats()
    # granite-8b: $0.0002/1K each → 1K*0.0002 + 1K*0.0002 = $0.0004
    assert abs(stats["total"]["cost_usd"] - 0.0004) < 1e-9


def test_load_stats_skips_malformed_lines(tmp_path, monkeypatch):
    import token_tracker
    log = tmp_path / "gen.jsonl"
    log.write_text('{"broken json\n{"model_id":"unknown","input_tokens":0,"output_tokens":0,"timestamp":"2026-04-22T00:00:00","type":"test"}\n', encoding="utf-8")
    monkeypatch.setattr(token_tracker, "LOG_PATH", log)

    stats = token_tracker.load_stats()
    assert stats["total"]["calls"] == 1  # only valid line counted


# ── pattern coverage sanity check ────────────────────────────────────────────

def test_pattern_count():
    assert len(DANGEROUS_PATTERNS) == 10


def test_all_patterns_have_valid_severity():
    valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    for _, _, sev in DANGEROUS_PATTERNS:
        assert sev in valid, f"Invalid severity: {sev}"
