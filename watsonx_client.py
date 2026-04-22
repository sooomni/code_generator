import logging
import os
import re
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.schema import TextGenParameters

from prompt_templates import SYSTEM_PROMPT

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_ID = "ibm/granite-8b-code-instruct"
MAX_NEW_TOKENS = 2048


@dataclass
class GenerationResult:
    code: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    model_id: str = MODEL_ID
    error: str | None = None


def _build_prompt(user_prompt: str) -> str:
    # Granite Code Instruct chat template
    return (
        f"<|system|>\n{SYSTEM_PROMPT}\n"
        f"<|user|>\n{user_prompt}\n"
        "<|assistant|>\n"
    )


def _extract_code(text: str) -> str:
    # 코드 블록(```python ... ``` 또는 ``` ... ```) 안의 내용 추출
    match = re.search(r"```(?:python)?\n([\s\S]+?)```", text)
    if match:
        return match.group(1).strip()
    # 코드 블록 없으면 전체 텍스트 반환
    return text.strip()


class WatsonxClient:
    def __init__(
        self,
        api_key: str | None = None,
        project_id: str | None = None,
        url: str = "https://us-south.ml.cloud.ibm.com",
    ):
        api_key = api_key or os.environ["WATSONX_API_KEY"]
        project_id = project_id or os.environ["WATSONX_PROJECT_ID"]
        url = os.environ.get("WATSONX_URL", url)

        credentials = Credentials(url=url, api_key=api_key)
        self._client = APIClient(credentials)
        self._project_id = project_id

    def generate_code(self, user_prompt: str, temperature: float = 0.2) -> GenerationResult:
        prompt = _build_prompt(user_prompt)

        params = TextGenParameters(
            temperature=temperature,
            max_new_tokens=MAX_NEW_TOKENS,
            repetition_penalty=1.05,
        )

        model = ModelInference(
            model_id=MODEL_ID,
            api_client=self._client,
            project_id=self._project_id,
            params=params,
        )

        start = time.perf_counter()
        try:
            response = model.generate(prompt=prompt)
            elapsed_ms = (time.perf_counter() - start) * 1000

            result = response["results"][0]
            raw = result.get("generated_text", "")
            code = _extract_code(raw)
            input_tokens = result.get("input_token_count", 0)
            output_tokens = result.get("generated_token_count", 0)

            logger.info(
                "Generated code in %.0fms (%d→%d tokens) stop_reason=%s",
                elapsed_ms, input_tokens, output_tokens,
                result.get("stop_reason", "?"),
            )

            if not code:
                logger.warning("Empty output. Raw response: %r", raw[:200])

            return GenerationResult(
                code=code,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=elapsed_ms,
            )

        except Exception as exc:
            logger.error("WatsonxClient error: %s", exc)
            return GenerationResult(
                code="", input_tokens=0, output_tokens=0,
                latency_ms=0, error=str(exc),
            )
