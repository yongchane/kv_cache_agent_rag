# 팀 코드와 도메인·추적 통합 — 2026-10-07

작업 브랜치: `feature/hyc-domain-tracing`. main은 변경하지 않았다.

## 출처와 개인 역할

사용자가 전달한 Downloads의 Agent_판교캠퍼스_7반 팀 폴더에서 `graph.py`, `state.py`,
`agents/synthesis.py`, `app.py`, `llm.py`, `README.md`, `tests/test_smoke.py`를 반영했다.
팀원의 Orchestrator·품질 평가 기본 구현을 현용찬 개인 구현으로 주장하지 않는다.

현용찬 담당 통합 변경:

- 기존 도메인 계약을 팀의 `current_task`에 연결하고 feedback·queries·attempt를 평가 함수로 전달.
- 팀 State의 `task_results`, `quality_evaluation`, `decision_log`를 로컬·원격 추적 요약에 연결.
- State trace_id를 root LangSmith run ID와 통일. commit 및 미커밋 변경 유무 기록.
- OpenAI SDK 래핑 유지. 원격 Client 입력·출력 sanitizer를 사용해 프롬프트·응답·보고서 원문 대신 제어 요약만 전송.
- SDK flush 후 서버 read_run을 최대 3회 확인. 수집 요청과 서버 확인을 구분.
- 요청한 관점만 validation 대상에 포함; task_results에서 이전 attempt를 찾아 재시도 횟수 증가.
- Orchestrator 품질 이슈/누락을 도메인 재검색에 전달. 시장성·이해관계자 등 다른 Agent가 feedback를 사용하는 개선은 아직 별도다.
- 도메인 부족/오류는 기존 validation이 확인할 수 있도록 parse_error로 연결한다.
- 실제 실행 CLI는 status=success와 원격 기록 확인을 분리한다. warning은 정상 품질 합격으로 표시하지 않는다.

## 검증과 한계

실제 팀 `build_graph()`를 실행하되 외부 검색·LLM만 mock으로 치환해 요청 관점 제한,
도메인 부분 재시도, attempt 1→2, 영구 실패 상한 종료, State/run ID 일치를 검사했다.
원격 Client의 sanitizer 설정 및 같은 run 조회 판정은 mock 테스트이며 실제 서버 실증이 아니다.

실제 LangSmith 키가 없어 원격 캡처는 미완료. 기존 OpenAI 인증 오류도 해소됐다고 주장하지 않는다.
팀 공유본 `local_trace.json/png`는 이전 구조 증빙이라 복사하지 않았다. 최종 코드를 실행해 새 캡처가 필요하다.
보고서의 groundedness는 현재 근거 ID 등록 검사이며 주장별 의미 검증이 아니다.
checkpointer는 없어 중단 후 자동 재개는 구현되지 않았다.

## 제출 전

1. 로컬 `.env`에 팀 계정 키·프로젝트·지역 설정을 입력한다. 실제 키를 Git이나 대화에 넣지 않는다.
2. 2/3/4개 관점 요청, 도메인 재작업, 품질 보고서 재생성, 종료를 실제 입력으로 실행한다.
3. 깨끗한 commit에서 실행하고 manifest의 commit/run ID를 캡처·보고서와 연결한다.
4. 실제 LangSmith UI 캡처를 순서대로 저장한다. fixture/mock은 실서비스 증빙이 아니다.
