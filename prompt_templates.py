SYSTEM_PROMPT = """You are an expert Python code generator.
Generate clean, production-ready Python code with:
- Type hints on all function parameters and return values
- A concise docstring (one-line summary + Args/Returns if non-trivial)
- Proper error handling where appropriate

Return ONLY the Python code block — no explanations, no markdown fences."""


def build_function_prompt(function_name: str, description: str, context: str = "") -> str:
    parts = [f"Generate a Python function named `{function_name}`."]
    parts.append(f"Purpose: {description}")
    if context:
        parts.append(f"\nContext / surrounding code:\n{context}")
    parts.append("\nReturn only the function code.")
    return "\n".join(parts)


def build_class_prompt(class_name: str, description: str, methods: list[str] | None = None) -> str:
    parts = [f"Generate a Python class named `{class_name}`."]
    parts.append(f"Purpose: {description}")
    if methods:
        parts.append("Include these methods: " + ", ".join(methods))
    parts.append("\nReturn only the class code.")
    return "\n".join(parts)


def build_test_prompt(source_code: str) -> str:
    return (
        "Generate pytest unit tests for the following Python code.\n"
        "Cover normal cases, edge cases, and error cases.\n\n"
        f"Source code:\n{source_code}\n\n"
        "Return only the test code."
    )


def build_explain_prompt(source_code: str) -> str:
    return (
        "Explain the following Python code concisely.\n"
        "Focus on what it does, any important side-effects, and potential issues.\n\n"
        f"{source_code}"
    )
