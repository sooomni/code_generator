import ast
import re
from dataclasses import dataclass, field
from typing import Literal

SeverityLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

# (pattern, label, severity)
DANGEROUS_PATTERNS: list[tuple[str, str, SeverityLevel]] = [
    # CRITICAL — arbitrary code execution
    (r"\beval\s*\(",                              "eval() usage",                    "CRITICAL"),
    (r"\bexec\s*\(",                              "exec() usage",                    "CRITICAL"),
    (r"__import__\s*\(",                          "__import__() usage",              "CRITICAL"),
    (r"subprocess\.[a-z_]+\s*\(.*shell\s*=\s*True", "subprocess shell=True",        "CRITICAL"),
    (r"os\.system\s*\(",                          "os.system() usage",               "CRITICAL"),
    # HIGH — deserialization / injection
    (r"pickle\.loads?\s*\(",                      "pickle deserialization",           "HIGH"),
    (r"yaml\.load\s*\([^)]*\)",                   "yaml.load() without Loader",      "HIGH"),
    (r"""(?:execute|executemany)\s*\(\s*[f"'].*%|\.format\(|f["']""",
                                                  "potential SQL injection",          "HIGH"),
    # MEDIUM — data exposure / weak crypto
    (r"hashlib\.(md5|sha1)\s*\(",                 "weak hashing algorithm",          "MEDIUM"),
    # LOW — permissive file operations
    (r"open\s*\([^)]+,\s*['\"]w",                "file write operation",            "LOW"),
]

SEVERITY_ORDER: dict[SeverityLevel, int] = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}

SEVERITY_PENALTY: dict[SeverityLevel, int] = {
    "CRITICAL": 30,
    "HIGH": 20,
    "MEDIUM": 10,
    "LOW": 5,
}


@dataclass
class SecurityIssue:
    label: str
    severity: SeverityLevel


@dataclass
class ValidationResult:
    is_valid: bool
    syntax_ok: bool
    security_issues: list[str] = field(default_factory=list)          # kept for API compat
    security_details: list[SecurityIssue] = field(default_factory=list)
    risk_level: SeverityLevel | None = None
    quality_score: int = 0
    quality_notes: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def confidence_score(self) -> int:
        if not self.syntax_ok:
            return 0
        penalty = sum(SEVERITY_PENALTY[i.severity] for i in self.security_details)
        return max(self.quality_score - min(penalty, 60), 0)


def _overall_risk(issues: list[SecurityIssue]) -> SeverityLevel | None:
    if not issues:
        return None
    return max(issues, key=lambda i: SEVERITY_ORDER[i.severity]).severity


def validate(code: str) -> ValidationResult:
    # 1. Syntax check
    try:
        tree = ast.parse(code)
        syntax_ok = True
    except SyntaxError as exc:
        return ValidationResult(
            is_valid=False,
            syntax_ok=False,
            error=f"SyntaxError at line {exc.lineno}: {exc.msg}",
        )

    # 2. Security scan
    details: list[SecurityIssue] = [
        SecurityIssue(label=label, severity=severity)
        for pattern, label, severity in DANGEROUS_PATTERNS
        if re.search(pattern, code, re.DOTALL)
    ]
    security_issues = [d.label for d in details]
    risk_level = _overall_risk(details)

    # 3. Quality checks
    quality_score = 100
    quality_notes: list[str] = []

    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

    missing_docstrings = [
        f.name for f in functions
        if not (f.body and isinstance(f.body[0], ast.Expr)
                and isinstance(f.body[0].value, ast.Constant))
    ]
    if missing_docstrings:
        quality_score -= 15
        quality_notes.append(f"Missing docstrings: {', '.join(missing_docstrings)}")

    missing_annotations = [
        f.name for f in functions
        if not (f.returns and all(a.annotation for a in f.args.args))
    ]
    if missing_annotations:
        quality_score -= 10
        quality_notes.append(f"Missing type hints: {', '.join(missing_annotations)}")

    if len(code.splitlines()) > 200:
        quality_score -= 5
        quality_notes.append("File is long (>200 lines) — consider splitting")

    is_valid = syntax_ok and not security_issues
    return ValidationResult(
        is_valid=is_valid,
        syntax_ok=syntax_ok,
        security_issues=security_issues,
        security_details=details,
        risk_level=risk_level,
        quality_score=max(quality_score, 0),
        quality_notes=quality_notes,
    )
