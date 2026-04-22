import json
import logging
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from watsonx_client import WatsonxClient
from code_validator import validate
from prompt_templates import (
    build_class_prompt,
    build_explain_prompt,
    build_function_prompt,
    build_test_prompt,
)

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Code Generator", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

watsonx = WatsonxClient()

# ── Request / Response models ─────────────────────────────────────────────────
class GenerateFunctionRequest(BaseModel):
    function_name: str
    description: str
    context: str = ""

class GenerateClassRequest(BaseModel):
    class_name: str
    description: str
    methods: list[str] = []

class GenerateTestRequest(BaseModel):
    source_code: str

class ValidateRequest(BaseModel):
    code: str

class ExplainRequest(BaseModel):
    source_code: str

class GenerateResponse(BaseModel):
    code: str
    validation: dict
    latency_ms: float
    tokens_used: int
    confidence_score: int
    timestamp: str

# ── Helpers ───────────────────────────────────────────────────────────────────
def _log_generation(request_type: str, result, validation) -> None:
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": request_type,
        "latency_ms": result.latency_ms,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "syntax_ok": validation.syntax_ok,
        "is_valid": validation.is_valid,
        "confidence_score": validation.confidence_score,
        "security_issues": validation.security_issues,
    }
    with open(LOG_DIR / "generations.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _generate_and_respond(prompt: str, request_type: str) -> GenerateResponse:
    result = watsonx.generate_code(prompt)
    if result.error:
        raise HTTPException(status_code=502, detail=result.error)

    validation = validate(result.code)
    _log_generation(request_type, result, validation)

    return GenerateResponse(
        code=result.code,
        validation={
            "syntax_ok": validation.syntax_ok,
            "is_valid": validation.is_valid,
            "security_issues": validation.security_issues,
            "quality_score": validation.quality_score,
            "quality_notes": validation.quality_notes,
        },
        latency_ms=result.latency_ms,
        tokens_used=result.input_tokens + result.output_tokens,
        confidence_score=validation.confidence_score,
        timestamp=datetime.utcnow().isoformat(),
    )


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "model": "ibm/granite-8b-code-instruct"}


@app.post("/generate/function", response_model=GenerateResponse)
def generate_function(req: GenerateFunctionRequest):
    prompt = build_function_prompt(req.function_name, req.description, req.context)
    return _generate_and_respond(prompt, "function")


@app.post("/generate/class", response_model=GenerateResponse)
def generate_class(req: GenerateClassRequest):
    prompt = build_class_prompt(req.class_name, req.description, req.methods or None)
    return _generate_and_respond(prompt, "class")


@app.post("/generate/tests", response_model=GenerateResponse)
def generate_tests(req: GenerateTestRequest):
    prompt = build_test_prompt(req.source_code)
    return _generate_and_respond(prompt, "tests")


@app.post("/validate")
def validate_code(req: ValidateRequest):
    result = validate(req.code)
    return {
        "syntax_ok": result.syntax_ok,
        "is_valid": result.is_valid,
        "security_issues": result.security_issues,
        "quality_score": result.quality_score,
        "quality_notes": result.quality_notes,
        "confidence_score": result.confidence_score,
        "error": result.error,
    }


@app.post("/explain")
def explain_code(req: ExplainRequest):
    result = watsonx.generate_code(build_explain_prompt(req.source_code), temperature=0.1)
    if result.error:
        raise HTTPException(status_code=502, detail=result.error)
    return {"explanation": result.code, "latency_ms": result.latency_ms}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
