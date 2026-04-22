import json
import logging
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from watsonx_client import WatsonxClient, SUPPORTED_MODELS, DEFAULT_MODEL_KEY
from code_validator import validate
from token_tracker import load_stats
from prompt_templates import (
    build_class_prompt,
    build_explain_prompt,
    build_function_prompt,
    build_test_prompt,
)

# ── Logging ───────────────────────────────────────────────────────────────────
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
app = FastAPI(title="AI Code Generator", version="1.1.0")
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
    model: str = DEFAULT_MODEL_KEY

class GenerateClassRequest(BaseModel):
    class_name: str
    description: str
    methods: list[str] = []
    model: str = DEFAULT_MODEL_KEY

class GenerateTestRequest(BaseModel):
    source_code: str
    model: str = DEFAULT_MODEL_KEY

class ValidateRequest(BaseModel):
    code: str

class ExplainRequest(BaseModel):
    source_code: str
    model: str = DEFAULT_MODEL_KEY

class GenerateResponse(BaseModel):
    code: str
    validation: dict
    latency_ms: float
    tokens_used: int
    confidence_score: int
    model_id: str
    timestamp: str

# ── Helpers ───────────────────────────────────────────────────────────────────
def _log_generation(request_type: str, result, validation) -> None:
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": request_type,
        "model_id": result.model_id,
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


def _generate_and_respond(prompt: str, request_type: str, model_key: str) -> GenerateResponse:
    result = watsonx.generate_code(prompt, model_key=model_key)
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
        model_id=result.model_id,
        timestamp=datetime.utcnow().isoformat(),
    )


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "supported_models": SUPPORTED_MODELS,
        "default_model": DEFAULT_MODEL_KEY,
    }


@app.post("/generate/function", response_model=GenerateResponse)
def generate_function(req: GenerateFunctionRequest):
    prompt = build_function_prompt(req.function_name, req.description, req.context)
    return _generate_and_respond(prompt, "function", req.model)


@app.post("/generate/class", response_model=GenerateResponse)
def generate_class(req: GenerateClassRequest):
    prompt = build_class_prompt(req.class_name, req.description, req.methods or None)
    return _generate_and_respond(prompt, "class", req.model)


@app.post("/generate/tests", response_model=GenerateResponse)
def generate_tests(req: GenerateTestRequest):
    prompt = build_test_prompt(req.source_code)
    return _generate_and_respond(prompt, "tests", req.model)


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


@app.get("/stats")
def get_stats():
    return load_stats()


@app.post("/explain")
def explain_code(req: ExplainRequest):
    result = watsonx.generate_code(
        build_explain_prompt(req.source_code),
        temperature=0.1,
        model_key=req.model,
    )
    if result.error:
        raise HTTPException(status_code=502, detail=result.error)
    return {
        "explanation": result.code,
        "latency_ms": result.latency_ms,
        "model_id": result.model_id,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
