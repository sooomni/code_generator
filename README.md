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
8. [트러블슈팅 이슈 정리](#트러블슈팅-이슈-정리)

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **함수 생성** | 함수명과 설명만 입력하면 타입 힌트·docstring 포함 Python 함수 생성 |
| **클래스 생성** | 클래스 역할과 메서드 목록으로 완성된 클래스 생성 |
| **테스트 생성** | 소스 코드 분석 후 정상·경계·오류 케이스 pytest 자동 생성 |
| **코드 검증** | 문법 오류, 보안 취약점(7종), 품질 점수 자동 분석 |
| **코드 설명** | 복잡한 코드를 자연어로 설명 |

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
          +---------|-------------------+
                    |
                    v
          +-----------------------------+
          |       IBM watsonx.ai        |
          |  granite-8b-code-instruct   |
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

### AI 모델

| 항목 | 값 |
|------|-----|
| 플랫폼 | IBM watsonx.ai |
| 모델 | `ibm/granite-8b-code-instruct` |
| 리전 | `us-south` (Dallas) |
| 프롬프트 포맷 | Granite Chat Template (`<\|system\|>` / `<\|user\|>` / `<\|assistant\|>`) |

### 코드 검증

| 검증 항목 | 방식 |
|----------|------|
| 문법 검사 | Python `ast.parse()` |
| 보안 검사 | 정규식 패턴 매칭 (eval, exec, os.system 등 7종) |
| 품질 점수 | AST 기반 docstring·타입힌트 검사 (0~100점) |
| 신뢰도 점수 | 품질 점수 − 보안 패널티 |

### Frontend

| 기술 | 용도 |
|------|------|
| Vanilla HTML/CSS/JS | 웹 데모 UI (`demo.html`) |
| VS Code Extension API | 에디터 통합 (`Ctrl+Shift+K`) |

---

## 프로젝트 구조

```
code_generator/
│
├── main.py                  # FastAPI 서버 — API 엔드포인트 정의
├── watsonx_client.py        # IBM watsonx API 호출 래퍼
├── code_validator.py        # 문법·보안·품질 검증 엔진
├── prompt_templates.py      # LLM 프롬프트 템플릿 모음
├── test_cases.py            # pytest 통합 테스트
├── demo.html                # 브라우저 기반 웹 데모 UI
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

### 4. VS Code 익스텐션 (개발 모드)

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

### 응답 예시 (`/generate/function`)

```json
{
  "code": "def calculate_discount(price: float, tier: str) -> float:\n    ...",
  "validation": {
    "syntax_ok": true,
    "is_valid": true,
    "security_issues": [],
    "quality_score": 100,
    "quality_notes": []
  },
  "latency_ms": 1243.5,
  "tokens_used": 312,
  "confidence_score": 100,
  "timestamp": "2026-04-22T03:27:00.000Z"
}
```

---

## 코드 검증 기준

### 보안 검사 항목 (7종)

| 패턴 | 위험 이유 |
|------|----------|
| `eval()` | 임의 코드 실행 |
| `exec()` | 임의 코드 실행 |
| `__import__()` | 동적 모듈 로드 |
| `subprocess(shell=True)` | 쉘 인젝션 |
| `os.system()` | OS 명령 실행 |
| `pickle.load()` | 역직렬화 취약점 |
| `open(..., 'w')` | 무단 파일 쓰기 |

### 품질 점수 산정

```
기본 점수: 100점
- docstring 누락 함수 존재: -15점
- 타입 힌트 누락 함수 존재: -10점
- 200줄 초과: -5점

신뢰도 = 품질 점수 - (보안 이슈 수 x 20점)
```

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

### 공통 교훈

| 항목 | 교훈 |
|------|------|
| 모델 선택 | 환경별 지원 모델 목록을 먼저 확인 (`foundation_model_specs` API) |
| 프롬프트 포맷 | 모델마다 전용 Chat Template이 다름 (Granite / Llama / Mistral 각각 상이) |
| Region | watsonx 프로젝트 생성 리전과 API URL 리전이 반드시 일치해야 함 |
