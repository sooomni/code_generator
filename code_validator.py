import ast
import re
from dataclasses import dataclass, field

DANGEROUS_PATTERNS = [
    (r"\beval\s*\(", "eval() usage"),
    (r"\bexec\s*\(", "exec() usage"),
    (r"__import__\s*\(", "__import__() usage"),
    (r"subprocess\.call\s*\(.*shell\s*=\s*True", "shell=True in subprocess"),
    (r"os\.system\s*\(", "os.system() usage"),
    (r"pickle\.loads?\s*\(", "pickle deserialization"),
    (r"open\s*\([^)]+,\s*['\"]w", "file write operation"),
]


@dataclass
class ValidationResult:
    is_valid: bool
    syntax_ok: bool
    security_issues: list[str] = field(default_factory=list)
    quality_score: int = 0          # 0–100
    quality_notes: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def confidence_score(self) -> int:
        if not self.syntax_ok:
            return 0
        penalty = min(len(self.security_issues) * 20, 40)
        return max(self.quality_score - penalty, 0)


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
    security_issues = [
        label for pattern, label in DANGEROUS_PATTERNS
        if re.search(pattern, code)
    ]

    # 3. Quality checks
    quality_score = 100
    quality_notes: list[str] = []

    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

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
        quality_score=max(quality_score, 0),
        quality_notes=quality_notes,
    )
