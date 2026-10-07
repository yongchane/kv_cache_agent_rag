# 현용찬 담당 구현·통합 안내

2026-10-07. 브랜치 `feature/hyc-domain-tracing`. 최신 원격 팀 main `bd9d7de`의 코드와 팀 역할표 기준으로 구현했다. 임유리·김선정의 새 Orchestrator/State/품질 코드가 아직 원격에 없으므로 아래 계약은 연결 가능한 제안이며 최종 합의 계약으로 표시하지 않는다.

## 변경 이유와 방법

| 파일 | 기존 문제 | 변경 내용 |
|---|---|---|
| `agents/domain_evaluation.py` | 정해진 두 기술·전체 기준만 조사; 재작업 요청 미사용 | 기술·기준·feedback·queries를 받는 task Worker. 실제 검색과 prompt에 반영 |
| 같은 파일 | 결과 dict의 형식·평가 누락·근거 기술이 검증되지 않음 | Pydantic 출력 검증, 기술×기준 커버리지·근거 ID/기술 일치 검사 |
| `observability.py` | 실행과 산출물의 연결 정보 부족 | Graph callbacks, thread-safe JSONL, UUID·commit·manifest·LangSmith run 확인 |
| `app.py` | Graph invoke만 실행 | TraceSession으로 호출, 보고서 파일을 같은 run manifest에 연결 |
| `config.py` | OpenAI SDK 호출의 내부 trace 없음 | tracing 활성화 시 공식 `wrap_openai`; 명령행 설정 우선 |
| `scripts/trace_run.py` | 계정 설정 확인·데모 실행 절차 없음 | 안전한 설정 확인·fixture·실제 실행 명령 제공 |
| `.env.example` | README가 안내한 샘플 파일 부재 | 실제 값 없는 설정 샘플 추가 |
| `tests/` | 이번 역할의 Worker/trace 통합 사례 없음 | 계약·실패·누락·동적 작업 수·재작업·상한 종료 테스트 |

도메인 Worker의 `success`는 출력 형식·요청 항목·근거 등록이 충족됐다는 의미다. 수치/주장이 원문 내용으로 실제 뒷받침되는지는 최종 quality Judge와 사람이 추가 검수한다.

## Orchestrator 담당자에게 전달할 계약

```python
from agents.domain_evaluation import evaluate_domain_task

result = evaluate_domain_task({
    "task_id": "domain-hbm-1",
    "technologies": ["DeepSeek-V2 MLA", "ITME"],
    "criteria": ["HBM memory usage"],
    "domain": "데이터센터·클라우드 LLM 서빙",
    "queries": ["HBM memory comparison baseline conditions"],
    "feedback": "두 기술의 실험 환경을 명시",
    "attempt": 1,
    "top_k": 2,
})
# result: task_id, view, attempt, status, analysis, references, gaps, error
```

`criteria`는 `DOMAIN_CRITERIA`의 문자열을 사용한다. Worker는 내부에서 retry하거나 다른 Agent를 호출하지 않는다. status는 `success / insufficient / error`. Orchestrator가 `gaps`를 추가질의로 구체화하고 attempt를 증가시켜 다시 호출한다. 두 기술을 모두 요구하면 같은 기준으로 평가하며 한 기술 task면 최종 기술 간 비교는 Synthesizer가 담당한다.

결과를 Graph State에 병합하는 adapter는 **팀 State 계약에 맞춰** 다음 형태로 연결한다.

```python
def domain_worker(state):
    result = evaluate_domain_task(state["task"])
    return {"worker_results": [result]}
```

`worker_results`는 동시 Worker가 쓰므로 reducer가 필요하다. 같은 task_id의 재시도 결과는 최신 attempt로 교체하고, 다른 task_id의 성공 결과는 유지한다. task_id는 계획 내에서 유일해야 한다. 기존 `domain_evaluation_agent`는 `domain_analysis / references / errors`를 반환해 기존 Graph와 호환한다. 최종 State 이름이 다르면 위 adapter만 조정하면 된다.

## Trace 연결 방법

```python
from pathlib import Path
from observability import TraceSession

session = TraceSession(Path("outputs/traces"), pattern="orchestrator_workers")
result = session.invoke(compiled_team_graph, initial_state)
session.attach_artifacts({"report": report_path})
```

State나 라우팅을 TraceSession이 변경하지 않는다. `tasks`, `worker_results`, `quality_verdict`, `decision`이 있으면 작업 수·ID·시도·판정·결정 사유가 로컬 로그에 요약된다. 팀이 다른 이름을 사용하면 `control_summary`에 mapping을 추가한다. `thread_id`를 전달해도 checkpointer가 없는 Graph에는 복구 기능이 생기지 않는다.

LangSmith와 로컬 trace 모두 run_id를 공유한다. `langsmith_verified=true`는 SDK flush 후 서버에서 해당 run을 조회한 경우에만 설정한다. `false`는 실제 LangSmith 캡처가 확보됐다는 의미가 아니다. local JSONL은 LangSmith tracing PNG를 대신하지 않는다.

## 실행

```bash
source .venv/bin/activate
python scripts/trace_run.py --check
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/test_smoke.py

# 외부 LLM·검색 없는 fixture. 정상/재시도/소진 흐름 확인용
python scripts/trace_run.py --fixture --task-count 1
python scripts/trace_run.py --fixture --task-count 2 --scenario retry
python scripts/trace_run.py --fixture --scenario exhaust
# exhaust의 exit 1은 예상 실패를 올바르게 기록한 결과

# 실제 논문 색인이 준비된 경우 1개 기준만 검색·LLM 확인
python scripts/domain_smoke.py

# 실제 키를 로컬 .env에 설정한 뒤 원격 연결 smoke
python scripts/trace_run.py --fixture --scenario retry --langsmith
# 현재 production Graph 실행. 팀 Graph 통합 전에는 baseline_static로 기록
FAST_MODE=false python scripts/trace_run.py --langsmith
```

실행 기록은 `outputs/traces/<UUID>/events.jsonl`, `manifest.json`에 저장한다. fixture manifest의 `fixture=true`를 유지하며 제출용 실제 실행으로 설명하지 않는다.

## 남은 사용자 작업

1. 임유리에게 DomainTask 입력·반환값을 전달하고 최종 task/State 필드 이름을 맞춘다.
2. 팀 LangSmith project와 지역/워크스페이스를 정한 후 `.env`에 실제 키를 설정한다. 대화에 키를 붙여 넣지 않는다.
3. 김선정의 quality 결과 필드와 Loop 경로를 받아 trace 요약에 연결한다.
4. 팀의 통합 브랜치에서 정상·다른 작업 수·실패 복구·품질 보완·상한 종료를 재검증한다.
5. 같은 commit/run의 LangSmith 화면을 캡처해 `tracing-1.png`, `tracing-2.png`로 저장한다.
6. 실제 기여를 README에 반영한다: 도메인 Worker·근거 검증·통합 테스트·실행 tracing 구현 및 검증.

최종 production Orchestrator와 평가 보고서 전체의 완료 여부는 이번 작업으로 확정하지 않는다.
