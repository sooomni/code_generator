# AI 코드 생성기 (AI Code Generator)

IBM watsonx와 Granite 코드 모델을 활용한 Python 코드 자동 생성 도구입니다.
함수·클래스 생성부터 테스트 자동화, 보안 검증, 코드 설명까지 개발 워크플로우 전반을 지원합니다.

---

## 목차

1. [주요 기능](#주요-기능)
2. [아키텍처](#아키텍처)
3. [기술 스택](#기술-스택)
4. [프로젝트 구조](#프로젝트-구조)
5. [실행 방법](#실행-방법)
6. [API 명세](#api-명세)
7. [코드 검증 기준](#코드-검증-기준)
8. [고도화 작업 내역](#고도화-작업-내역)
9. [트러블슈팅 이슈 정리](#트러블슈팅-이슈-정리)

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **함수 생성** | 함수명과 설명만 입력하면 타입 힌트·docstring 포함 Python 함수 생성 |
| **클래스 생성** | 클래스 역할과 메서드 목록으로 완성된 클래스 생성 |
| **테스트 생성** | 소스 코드 분석 후 정상·경계·오류 케이스 pytest 자동 생성 |
| **코드 검증** | 문법 오류, 보안 취약점(10종·심각도 판정), 품질 점수 자동 분석 |
| **코드 설명** | 복잡한 코드를 자연어로 설명 |
| **모델 선택** | Granite 8B / Llama 3.3 70B / Mistral Small 24B 중 선택 |
| **토큰 & 비용 추적** | API 호출 이력 기반 토큰 사용량 및 비용 분석, 월 예산 예측 |

---

## 아키텍처

```
  [VS Code Extension]        [Web UI - demo.html]
   Ctrl+Shift+K shortcut       Browser-based UI
          |                           |
          +-------------+-------------+
                        |
                   HTTP REST API
                        |
                        v
          +-----------------------------+
          |  FastAPI Server  (:8000)    |
          |                             |
          |  POST /generate/function    |
          |  POST /generate/class       |
          |  POST /generate/tests       |
          |  POST /validate             |
          |  POST /explain              |
          |  GET  /health               |
          |  GET  /stats                |
          |                             |
          |  +--------------+  +------+ |
          |  |watsonx_client|  | code | |
          |  |  LLM caller  |  | vali | |
          |  +------+-------+  | dator| |
          |         |          +------+ |
          |         |      +----------+ |
          |         |      | prompt_  | |
          |         |      | templates| |
          |         |      +----------+ |
          |         |      +----------+ |
          |         |      | token_   | |
          |         |      | tracker  | |
          |         |      +----------+ |
          +---------|-------------------+
                    |
                    v
          +-----------------------------+
          |       IBM watsonx.ai        |
          |  granite-8b-code-instruct   |
          |  llama-3-3-70b-instruct     |
          |  mistral-small-24b          |
          |  Region: us-south (Dallas)  |
          +-----------------------------+
```

---

## 기술 스택

### Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.12+ | 런타임 |
| FastAPI | 0.110+ | REST API 서버 |
| Uvicorn | 0.29+ | ASGI 웹 서버 |
| Pydantic | 2.6+ | 요청/응답 데이터 검증 |
| ibm-watsonx-ai | 1.1+ | IBM watsonx LLM 호출 |
| python-dotenv | 1.0+ | 환경변수 관리 |
| pytest | 9.0+ | 단위·통합 테스트 |

### AI 모델

| 항목 | 값 |
|------|-----|
| 플랫폼 | IBM watsonx.ai |
| 기본 모델 | `ibm/granite-8b-code-instruct` |
| 선택 모델 | `meta-llama/llama-3-3-70b-instruct`, `mistralai/mistral-small-3-1-24b-instruct-2503` |
| 리전 | `us-south` (Dallas) |
| 프롬프트 포맷 | Granite Chat Template (`<\|system\|>` / `<\|user\|>` / `<\|assistant\|>`) |

### 코드 검증

| 검증 항목 | 방식 |
|----------|------|
| 문법 검사 | Python `ast.parse()` |
| 보안 검사 | 정규식 패턴 매칭 (10종, 심각도 4단계) |
| 품질 점수 | AST 기반 docstring·타입힌트 검사 (0~100점) |
| 신뢰도 점수 | 품질 점수 − 심각도 가중 보안 패널티 |

### Frontend

| 기술 | 용도 |
|------|------|
| Vanilla HTML/CSS/JS | 웹 데모 UI (`demo.html`) |
| Prism.js | Python 신택스 하이라이트 + 줄 번호 |
| VS Code Extension API | 에디터 통합 (`Ctrl+Shift+K`) |

---

## 프로젝트 구조

```
code_generator/
│
├── main.py                  # FastAPI 서버 — API 엔드포인트 정의
├── watsonx_client.py        # IBM watsonx API 호출 래퍼 (모델 선택 지원)
├── code_validator.py        # 문법·보안(10종·심각도)·품질 검증 엔진
├── prompt_templates.py      # LLM 프롬프트 템플릿 모음
├── token_tracker.py         # 토큰 사용량·비용 추적 및 통계 집계
├── test_unit.py             # pytest 단위 테스트 (서버 불필요, 26개)
├── test_cases.py            # pytest 통합 테스트 (서버 필요)
├── demo.html                # 브라우저 기반 웹 데모 UI (다크/라이트 모드)
│
├── vscode-extension/
│   ├── extension.js         # VS Code 명령어 및 단축키 구현
│   ├── package.json         # 익스텐션 메타데이터 및 기여 항목 정의
│   └── src/
│       └── client.js        # FastAPI 서버 호출 클라이언트
│
├── logs/                    # 생성 이력 로그 (자동 생성, git 제외)
│   ├── app.log              # 서버 실행 로그
│   └── generations.jsonl    # 코드 생성 이력 (JSON Lines)
│
├── .env                     # 인증 정보 (git 제외)
├── .env.example             # 환경변수 설정 예시
├── requirements.txt         # Python 의존성
└── .gitignore
```

---

## 실행 방법

### 사전 요구사항
- Python 3.12 이상
- IBM Cloud 계정 + watsonx.ai 프로젝트
- IBM Cloud API Key (`IAM > API Keys`)

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/sooomni/code_generator.git
cd code_generator

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 API Key와 Project ID 입력
```

`.env` 파일:
```
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

### 2. 서버 실행

```bash
python main.py
# → http://localhost:8000 에서 서버 시작
# → http://localhost:8000/docs 에서 Swagger UI 확인 가능
```

### 3. 웹 UI 실행

`demo.html`을 브라우저에서 열면 됩니다.
서버가 실행 중이면 하단 상태바에 **서버 연결됨** 표시가 나타납니다.
우측 상단 버튼으로 다크/라이트 모드를 전환할 수 있습니다.

### 4. 테스트 실행

```bash
# 단위 테스트 (서버 불필요)
pytest test_unit.py -v

# 통합 테스트 (서버 실행 후)
python main.py &
pytest test_cases.py -v
```

### 5. VS Code 익스텐션 (개발 모드)

```bash
cd vscode-extension
# VS Code에서 F5 → Extension Development Host 실행
# Ctrl+Shift+K → 함수 생성
```

---

## API 명세

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 및 모델 상태 확인 |
| `POST` | `/generate/function` | Python 함수 생성 |
| `POST` | `/generate/class` | Python 클래스 생성 |
| `POST` | `/generate/tests` | pytest 테스트 생성 |
| `POST` | `/validate` | 코드 검증 (문법·보안·품질) |
| `POST` | `/explain` | 코드 자연어 설명 |
| `GET` | `/stats` | 토큰 사용량 및 비용 통계 |

### 요청 예시 (`/generate/function`)

```json
{
  "function_name": "calculate_discount",
  "description": "고객 등급과 원가를 받아 할인 적용 최종 가격 반환",
  "context": "",
  "model": "granite-8b"
}
```

`model` 값: `granite-8b` (기본값) | `llama-70b` | `mistral-small`

### 응답 예시 (`/generate/function`)

```json
{
  "code": "def calculate_discount(price: float, tier: str) -> float:\n    ...",
  "validation": {
    "syntax_ok": true,
    "is_valid": true,
    "security_issues": [],
    "security_details": [],
    "risk_level": null,
    "quality_score": 100,
    "quality_notes": []
  },
  "latency_ms": 1243.5,
  "tokens_used": 312,
  "confidence_score": 100,
  "model_id": "ibm/granite-8b-code-instruct",
  "timestamp": "2026-04-22T03:27:00.000Z"
}
```

### 응답 예시 (`/stats`)

```json
{
  "total": { "calls": 42, "input_tokens": 18500, "output_tokens": 9200, "total_tokens": 27700, "cost_usd": 0.005540 },
  "today": { "calls": 5, "input_tokens": 2100, "output_tokens": 980, "cost_usd": 0.000616 },
  "projection": { "avg_daily_cost_usd": 0.000554, "projected_monthly_usd": 0.0166, "active_days": 10 },
  "by_model": { "ibm/granite-8b-code-instruct": { "calls": 30, "total_tokens": 18000, "cost_usd": 0.0036 } },
  "by_type": { "function": 20, "class": 10, "tests": 12 },
  "daily_trend": [ { "date": "2026-04-22", "calls": 5, "tokens": 3080, "cost": 0.000616 } ],
  "pricing": { "ibm/granite-8b-code-instruct": { "input": 0.0002, "output": 0.0002 } }
}
```

---

## 코드 검증 기준

### 보안 검사 항목 (10종)

| 심각도 | 패턴 | 위험 이유 |
|--------|------|----------|
| `CRITICAL` | `eval()` | 임의 코드 실행 |
| `CRITICAL` | `exec()` | 임의 코드 실행 |
| `CRITICAL` | `__import__()` | 동적 모듈 로드 |
| `CRITICAL` | `subprocess(shell=True)` | 쉘 인젝션 |
| `CRITICAL` | `os.system()` | OS 명령 실행 |
| `HIGH` | `pickle.load()` | 역직렬화 취약점 |
| `HIGH` | `yaml.load()` | 안전하지 않은 YAML 역직렬화 |
| `HIGH` | `execute()` + 문자열 포맷팅 | SQL 인젝션 |
| `MEDIUM` | `hashlib.md5/sha1()` | 취약한 해시 알고리즘 |
| `LOW` | `open(..., 'w')` | 무단 파일 쓰기 |

### 품질 점수 산정

```
기본 점수: 100점
- docstring 누락 함수 존재: -15점
- 타입 힌트 누락 함수 존재: -10점
- 200줄 초과: -5점

신뢰도 = 품질 점수 - 심각도 가중 패널티
  CRITICAL 이슈당: -30점
  HIGH 이슈당:     -20점
  MEDIUM 이슈당:   -10점
  LOW 이슈당:       -5점
  (최대 -60점)
```

---

## 고도화 작업 내역

초기 버전(IBM watsonx 연동 기본 구현) 이후 아래 5개 기능을 단계적으로 추가했습니다.

### Priority 1 — 모델 선택 기능

**구현 내용**
- `watsonx_client.py`에 `SUPPORTED_MODELS` 딕셔너리 추가 (granite-8b / llama-70b / mistral-small)
- 모든 생성·설명 엔드포인트에 `model: str` 파라미터 추가
- 웹 UI 사이드바 최상단에 모델 선택 카드 UI 추가 (색상 도트로 모델 구분)

**효과**
- 작업 특성에 따라 최적 모델 선택 가능
- Granite 8B(코드 특화), Llama 70B(범용 대형), Mistral Small(경량 고성능)

---

### Priority 2 — 토큰 사용량 & 비용 추적

**구현 내용**
- `token_tracker.py` 신규 작성: `generations.jsonl` 로그 파싱으로 통계 집계
- 모델별 단가 테이블 (`PRICING`) 기반 비용 자동 계산
- `GET /stats` 엔드포인트 추가
- 웹 UI에 **토큰 & 비용** 탭 추가
  - 요약 카드 4개 (총 호출 횟수, 총 토큰, 누적 비용, 월 예상 비용)
  - 기능별/모델별 바 차트, 최근 7일 트렌드

**효과**
- API 비용 실시간 모니터링 및 월 예산 예측 가능

---

### Priority 3 — 보안 검사 강화

**구현 내용**
- 보안 패턴 7종 → 10종 확대 (추가: `yaml.load`, SQL injection, `hashlib.md5/sha1`)
- 각 패턴에 `CRITICAL / HIGH / MEDIUM / LOW` 심각도 부여
- `ValidationResult`에 `security_details`(label+severity 목록) 및 `risk_level`(최고 심각도) 추가
- 신뢰도 점수 패널티를 심각도 가중치 기반으로 변경 (기존: 이슈당 고정 -20점)
- API 응답 및 웹 UI에 심각도 배지(CRITICAL/HIGH/MEDIUM/LOW) 표시

**효과**
- 단순 탐지에서 위험도 기반 판단으로 고도화
- 개발자가 우선 수정해야 할 이슈를 즉시 파악 가능

---

### Priority 4 — 웹 UI 개선

**구현 내용**
- **신택스 하이라이트**: Prism.js 적용으로 생성된 Python 코드에 문법 색상 + 줄 번호 표시
- **다크/라이트 모드 토글**: 헤더 버튼으로 전환, `localStorage`에 설정 저장
- CSS 변수로 라이트 테마 정의 (모든 색상·배경 전환 지원)
- 모드 전환 시 0.25s 부드러운 트랜지션

**효과**
- 생성된 코드 가독성 대폭 향상
- 사용 환경(라이트/다크)에 맞는 UI 선택 가능

---

### Priority 5 — pytest 테스트 코드

**구현 내용**
- `test_unit.py` 신규 작성: 서버 없이 실행 가능한 단위 테스트 **26개**
  - 문법 검사 (정상/오류/빈 코드)
  - 10종 보안 패턴별 탐지 및 심각도 검증 (`@pytest.mark.parametrize` 활용)
  - 위험도 최고값 결정 로직 (CRITICAL > HIGH > MEDIUM > LOW)
  - 품질 점수 및 신뢰도 패널티 계산
  - 토큰 비용 계산, 잘못된 JSON 라인 스킵 처리
- `test_cases.py` 확장: 서버 통합 테스트에 신규 기능 커버리지 추가
  - 모델 선택 파라미터 동작 검증
  - `security_details`, `risk_level` 응답 필드 검증
  - `/stats` 엔드포인트 응답 구조 검증
  - `scope="session"` 픽스처로 서버 미실행 시 자동 skip 처리

**효과**
- 핵심 로직을 오프라인에서 빠르게 검증 가능 (0.14초)
- 신규 패턴 추가 시 회귀 테스트 자동화

---

## 트러블슈팅 이슈 정리

### 이슈 1 — watsonx 프로젝트 접근 불가 (404)

**증상:** `404 Not Found` — 프로젝트를 찾을 수 없음

**원인:** 생성한 watsonx 프로젝트가 `us-south` region이 아닌 Tokyo(`jp-tok`) region에 있었음

**해결:** `WATSONX_URL`을 `jp-tok`으로 변경하여 404 해결 확인 후, Dallas용 신규 프로젝트 생성으로 최종 해결

---

### 이슈 2 — 지원되지 않는 모델

**증상:** `Model 'ibm/granite-34b-code-instruct' is not supported for this environment`

**원인:** 해당 프로젝트 환경에서 `granite-34b` 모델 미지원
- Tokyo 리전: `granite-34b` 없음 → `llama-3-3-70b-instruct`로 임시 변경
- Dallas 리전: `granite-34b` 없음 → `granite-8b-code-instruct`로 변경

**해결:** 최종적으로 `ibm/granite-8b-code-instruct` 사용

---

### 이슈 3 — 코드 생성 결과가 화면에 표시 안 됨

**증상:** API 호출은 성공(`200 OK`)인데 웹 UI에 코드 미표시, 로그에 `132→1 tokens`

**원인:** 두 가지 복합 문제
1. `stop_sequences=["```\n\n"]`가 즉시 트리거되어 1토큰만 생성
2. `ibm/granite-8b-code-instruct` 모델 전용 프롬프트 포맷 미적용

**해결:**
- `stop_sequences` 제거
- Granite Chat Template 적용 (`<|system|>` / `<|user|>` / `<|assistant|>`)
- 응답에서 코드 블록 추출 로직 (`_extract_code`) 추가

---

### 이슈 4 — pandas 설치 실패

**증상:** `installing build dependencies for pandas did not run successfully`

**원인:** Python 3.14 (pre-release) 사용으로 pandas 바이너리 wheel 미제공

**해결:** Python 3.12로 환경 변경

---

### 이슈 5 — SQL injection 패턴 오탐 (false positive)

**증상:** `f"Hello, {name}!"` 같은 일반 f-string 코드가 SQL injection으로 탐지됨

**원인:** 보안 패턴 정규식 `f["']`이 `execute()` 컨텍스트 없이 단독으로 매칭됨

**해결:** 패턴을 `(?:execute|executemany)\s*\([^)]*(?:%[^%]|\.format\s*\(|f["'])`로 수정,
`execute`/`executemany` 호출 내에서만 탐지하도록 범위 한정

---

### 공통 교훈

| 항목 | 교훈 |
|------|------|
| 모델 선택 | 환경별 지원 모델 목록을 먼저 확인 (`foundation_model_specs` API) |
| 프롬프트 포맷 | 모델마다 전용 Chat Template이 다름 (Granite / Llama / Mistral 각각 상이) |
| Region | watsonx 프로젝트 생성 리전과 API URL 리전이 반드시 일치해야 함 |
| 정규식 보안 패턴 | 범위를 좁게 정의하지 않으면 false positive 발생 — 단위 테스트로 오탐 검증 필수 |
