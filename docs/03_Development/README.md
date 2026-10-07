# 팀 분담과 2일 개발 계획

## 역할 제안

최신 README에 기록된 이전 커밋 역할을 바탕으로 제안한다. 이름은 가나다순이다. Contributors에는 마감 시 실제 수행한 구현·검증만 적고 PM/PL 표현은 쓰지 않는다.

| 팀원 | 이번 작업 제안 | 맡을 파일·산출물 | 완료 확인 |
|---|---|---|---|
| 곽민규 | 이해관계자 Agent 재작업 계약, 기대·우려 근거 균형 검수 | `agents/stakeholder_evaluation.py`, 이해관계자 사례 | feedback에 따라 질의가 바뀌고 부족한 근거 반환 |
| 김선정 | Supervisor·Graph 통합, 보고서 생성과 품질 Loop | `graph.py`, 신규 `agents/supervisor.py`·`agents/quality.py`, `agents/synthesis.py` | 조건부 라우팅·복귀·생성 후 평가·유한 종료 |
| 이지원 | 시장성 Agent와 출처 독립성·편향 통제 | `agents/market_evaluation.py`, 시장 재조사 사례 | 단일 출처 편중 감지와 추가 검색 질의 반영 |
| 임유리 | State·Agent 계약, 기술/TRL 근거 판정, reducer·복구 검증 | `state.py`, `agents/technical_research.py`, 관련 테스트 | 구조화 결과·상한·근거 ID 병합·checkpoint 범위 |
| 현용찬 | 도메인 Agent, Retriever 평가, trace 증빙·최종 제출 정합성 | `agents/domain_evaluation.py`, `evaluate.py`, 실행·검증 문서 | 재작업 질의 반영·지표 실제 측정·코드/trace/보고서 대조 |

공통 통합 파일 `graph.py`, `state.py`, `app.py`는 각자 동시에 수정하지 않는다. 계약 변경은 작업 시작 전에 공유하고 통합 담당자가 합친다. 코드를 맡은 사람이 자기 사례의 테스트와 짧은 설명까지 제공하면 보고서 담당자가 내용을 추측하지 않아도 된다.

## DAY 1

1. **첫 30분:** 패턴과 역할 확정, 네 관점 입력/출력, 완료·실패 조건 합의. `.env.example`·실행 환경·LangSmith 연결 확인.
2. **다음 60~90분:** Supervisor/State 담당자가 mock Agent로 정상·특정 관점 재작업·상한 종료 Graph를 먼저 만든다. 다른 팀원은 같은 결과 계약으로 각 관점 adapter를 만든다.
3. **오후:** 실제 RAG/웹/LLM 연결. 네 관점 Agent가 Supervisor로 복귀하는지 확인. Judge와 보고서 피드백 입력을 연결한다.
4. **퇴근 전:** 정상 1건과 재작업 1건을 실제 trace로 확인. 실패·미완료 항목을 issue/작업표에 남기고 제출 보고서 초안을 확보한다.

## DAY 2

1. 오전: 실패 경로·품질 Loop·근거 인용 검증, checkpoint 범위 확인. 수정 후 회귀 검증.
2. 점심 전후: 최종 환경에서 실제 실행하고 report·verdict·trace metadata 저장. Retriever Hit@5/MRR은 별도 실행해 실제 수치 기록.
3. 오후: 보고서 사실·중립성 검수, PDF 쪽수 확인, README/Contributors/그래프 업데이트.
4. 마감 전: 깨끗한 checkout에서 실행 재현, Git branch URL·PNG·PDF 확인, 정해진 파일명으로 ZIP 구성.

## 작업 공유 방법

각 작업은 다음 다섯 가지로 공유한다: **담당 파일 / 현재 변경 / 검증 명령과 결과 / 통합에 필요한 계약 / 막힌 점**. '완료'라고만 공유하지 않는다. 재작업 데모에는 어떤 근거를 왜 부족하게 만들었고 어떤 Agent가 다시 실행됐는지 남긴다. 고의 부족 사례는 검증용임을 표시한다.

브랜치 예시: `agent/supervisor`, `agent/state-technical`, `agent/market`, `agent/stakeholder`, `agent/domain-evaluation`. 통합 대상은 팀이 정한 과제 브랜치 하나로 맞춘다. 현재 문서 브랜치는 `agent-orchestration/planning-20261007`이며 구현 완료 브랜치가 아니다.

## 실행 준비

프로젝트 루트에서 아래를 실행한다. 이 명령들은 실행 준비 지침이며 이번 세션에서 전체 설치·서비스 실행을 완료한 것은 아니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
brew install pango
ollama pull qwen3-embedding:0.6b
# Ollama 서버가 실행 중인지 확인
python tests/test_smoke.py
FAST_MODE=false python app.py
python evaluate.py
```

현재 `.env.example`가 없으므로 담당자가 아래 키 이름만 담은 샘플을 추가한다. 실제 값은 로컬 `.env`에 둔다. LangSmith는 키 소유 계정·workspace·project에서 실제 trace를 확인해야 한다.

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=qwen3-embedding:0.6b
OLLAMA_HOST=http://localhost:11434
TAVILY_API_KEY=
FAST_MODE=false
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=kv-cache-agent-orchestration
```

지금 `llm.py`는 OpenAI SDK 직접 호출이다. Graph trace와 별도로 LLM 세부 호출도 남기려면 공식 SDK wrapper/trace 계측이 필요하다. [LangGraph tracing 공식 안내](https://docs.langchain.com/langsmith/trace-with-langgraph)를 확인한다. 계정 설정만으로 모든 외부 호출 사유가 자동 기록된다고 가정하지 않는다.

## 구현 전 테스트 기준

| 사례 | 입력/조건 | 통과 기준 |
|---|---|---|
| 정상 완료 | 네 관점 근거 충족 | Supervisor가 충분성 확인→종합→보고서→quality pass→END |
| 동적 첫 라우팅 | 시장 결과만 누락 / 도메인 결과만 누락을 각각 전달 | 누락 관점에 따라 다음 target가 달라짐 |
| 선택적 재작업 | 시장 근거만 insufficient | 시장 Agent만 재호출; 다른 관점 완료 결과 보존 |
| 재작업 입력 활용 | '도입 사례와 독립 출처 부족' feedback | 추가 질의가 기존 질의와 달라지고 결과에 대응 근거 연결 |
| Agent 실패 후 복구 | 시장 Agent 첫 호출 timeout, 다음 성공 | 제한된 재시도와 오류 기록, 정상 후속 처리 |
| 영구 실패 | 같은 관점 계속 error/insufficient | 상한에서 failed 종료; 성공 보고서로 표시하지 않음 |
| 잘못된 인용 | 존재하지 않는 ID·형식 오류·근거 없는 수치 | Groundedness fail, 필요한 관점 재조사 |
| 품질 재작성 | 근거는 충분하나 '무조건 우수/추천' 문구 | quality fail→보고서 재작성→재평가 |
| 관점 누락 | 시장 절은 있으나 실질 내용 없음 | coverage fail; 필요 관점 재작업 |
| 근거 병합 | 동일 ID 반복, 동일 URL에 서로 다른 ID | 중복은 억제하되 기존 인용 ID를 유실하지 않음 |
| 복구 | checkpoint 후 중단 | 같은 thread_id에서 저장된 완료 결과를 사용; 메모리/영속 복구 범위 구분 |
| 제출 출력 | 실제 최종 생성 | 10쪽 이하 PDF, SUMMARY·REFERENCE, 동일 run_id 증빙 |

mock 테스트 통과와 실제 LLM/검색 실행 성공은 따로 보고한다. 보고서·LangSmith 캡처에는 실제 실행 결과만 제출하며, mock 성공을 실서비스 성공으로 설명하지 않는다.
