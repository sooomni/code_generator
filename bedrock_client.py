import json
import logging
import time
from dataclasses import dataclass, field

import boto3
from botocore.exceptions import ClientError

from prompt_templates import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
MAX_TOKENS = 4096


@dataclass
class GenerationResult:
    code: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    model_id: str = MODEL_ID
    error: str | None = None


class BedrockClient:
    def __init__(self, region: str = "us-east-1"):
        self._client = boto3.client("bedrock-runtime", region_name=region)

    def generate_code(self, user_prompt: str, temperature: float = 0.2) -> GenerationResult:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "temperature": temperature,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        start = time.perf_counter()
        try:
            response = self._client.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            payload = json.loads(response["body"].read())
            code = payload["content"][0]["text"].strip()
            usage = payload.get("usage", {})

            logger.info("Generated code in %.0fms (%d→%d tokens)", elapsed_ms,
                        usage.get("input_tokens", 0), usage.get("output_tokens", 0))

            return GenerationResult(
                code=code,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                latency_ms=elapsed_ms,
            )

        except ClientError as exc:
            error_msg = exc.response["Error"]["Message"]
            logger.error("Bedrock ClientError: %s", error_msg)
            return GenerationResult(code="", input_tokens=0, output_tokens=0,
                                    latency_ms=0, error=error_msg)
        except Exception as exc:
            logger.error("Unexpected error calling Bedrock: %s", exc)
            return GenerationResult(code="", input_tokens=0, output_tokens=0,
                                    latency_ms=0, error=str(exc))
