import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# IBM watsonx 모델별 요금 (USD / 1K tokens)
PRICING: dict[str, dict[str, float]] = {
    "ibm/granite-8b-code-instruct":                  {"input": 0.0002, "output": 0.0002},
    "meta-llama/llama-3-3-70b-instruct":             {"input": 0.0009, "output": 0.0009},
    "mistralai/mistral-small-3-1-24b-instruct-2503": {"input": 0.0006, "output": 0.0006},
}
DEFAULT_PRICE = {"input": 0.0005, "output": 0.0005}

LOG_PATH = Path(__file__).parent / "logs" / "generations.jsonl"


def _cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICING.get(model_id, DEFAULT_PRICE)
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1000


def load_stats() -> dict:
    records: list[dict] = []
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    total_input = total_output = 0
    total_cost = 0.0
    by_model: dict[str, dict] = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "calls": 0})
    by_day:   dict[str, dict] = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "calls": 0})
    by_type:  dict[str, int]  = defaultdict(int)

    today = datetime.now(timezone.utc).date().isoformat()
    today_input = today_output = 0
    today_cost = 0.0

    for r in records:
        inp  = r.get("input_tokens", 0)
        out  = r.get("output_tokens", 0)
        mid  = r.get("model_id", "unknown")
        cost = _cost(mid, inp, out)
        day  = r.get("timestamp", "")[:10]

        total_input  += inp
        total_output += out
        total_cost   += cost

        by_model[mid]["input_tokens"]  += inp
        by_model[mid]["output_tokens"] += out
        by_model[mid]["cost"]          += cost
        by_model[mid]["calls"]         += 1

        by_day[day]["input_tokens"]  += inp
        by_day[day]["output_tokens"] += out
        by_day[day]["cost"]          += cost
        by_day[day]["calls"]         += 1

        by_type[r.get("type", "unknown")] += 1

        if day == today:
            today_input  += inp
            today_output += out
            today_cost   += cost

    # 일 평균 → 월 예측
    active_days = len(by_day) or 1
    avg_daily_cost = total_cost / active_days
    projected_monthly = avg_daily_cost * 30

    # 최근 7일 트렌드
    sorted_days = sorted(by_day.keys())[-7:]
    daily_trend = [
        {
            "date": d,
            "calls": by_day[d]["calls"],
            "tokens": by_day[d]["input_tokens"] + by_day[d]["output_tokens"],
            "cost": round(by_day[d]["cost"], 6),
        }
        for d in sorted_days
    ]

    return {
        "total": {
            "calls": len(records),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "cost_usd": round(total_cost, 6),
        },
        "today": {
            "calls": by_day.get(today, {}).get("calls", 0),
            "input_tokens": today_input,
            "output_tokens": today_output,
            "cost_usd": round(today_cost, 6),
        },
        "projection": {
            "avg_daily_cost_usd": round(avg_daily_cost, 6),
            "projected_monthly_usd": round(projected_monthly, 4),
            "active_days": active_days,
        },
        "by_model": {
            mid: {
                "input_tokens": v["input_tokens"],
                "output_tokens": v["output_tokens"],
                "total_tokens": v["input_tokens"] + v["output_tokens"],
                "cost_usd": round(v["cost"], 6),
                "calls": v["calls"],
            }
            for mid, v in by_model.items()
        },
        "by_type": dict(by_type),
        "daily_trend": daily_trend,
        "pricing": PRICING,
    }
