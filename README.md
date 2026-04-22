# AI 코드 생성기 (AI Code Generator)

IBM watsonx와 Granite 코드 모델을 활용한 Python 코드 자동 생성 도구입니다.
함수·클래스 생성부터 테스트 자동화, 보안 검증, 코드 설명까지 개발 워크플로우 전반을 지원합니다.

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
┌─────────────────────────────────────────────────────┐
│                    클라이언트                         │
│                                                     │
│   ┌─────────────────┐    ┌──────────────────────┐   │
│   │  VS Code 익스텐션 │    │   웹 UI (demo.html)   │   │
│   │  (Ctrl+Shift+K) │    │   브라우저에서 실행    │   │
│   └────────┬────────┘    └──────────┬───────────┘   │
└────────────┼─────────────────────────┼──────────────┘
             │  HTTP REST API          │
             ▼                         ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI 서버 (main.py :8000)            │
│                                                     │
│  POST /generate/function   POST /generate/class     │
│  POST /generate/tests      POST /validate           │
│  POST /explain             GET  /health             │
│                                                     │
│  ┌──────────────────┐   ┌─────────────────────────┐ │
│  │  watsonx_client  │   │     code_validator       │ │
│  │  (LLM 호출)       │   │  (AST + 보안 + 품질)    │ │
│  └────────┬─────────┘   └─────────────────────────┘ │
│           │              ┌─────────────────────────┐ │
│           │              │   prompt_templates       │ │
│           │              │  (프롬프트 템플릿 관리)   │ │
│           │              └─────────────────────────┘ │
└───────────┼─────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────┐
│   IBM watsonx.ai           │
│   ibm/granite-8b-code-    │
│   instruct                │
│   (us-south region)       │
└───────────────────────────┘
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

신뢰도 = 품질 점수 - (보안 이슈 수 × 20점)
```
