# Multi-Agent Orchestration 실습 시작 안내

> 팀 결정 갱신: **Orchestrator-Workers 강화**. 아래 Supervisor 추천은 초기 검토안입니다. 최신 [선택 근거](05_Decisions/Orchestrator_Selection.md)와 [도메인·Trace 작업 결과](03_Development/Domain_Tracing_Handoff.md)를 우선합니다.

기준일: 2026-10-07. 코드 분석 기준: 팀 원본 `upstream/main`의 `bd9d7de`. 이번 브랜치는 분석·설계·팀 작업 준비용이며, 아래 Supervisor 구조는 구현 예정인 제안이다.

## 먼저 볼 문서

1. [과제 요구사항과 현재 코드 차이](01_Project_Overview/README.md)
2. [Supervisor 아키텍처와 State 계약](02_Architecture/README.md)
3. [팀 분담·2일 진행 순서·개발 검증](03_Development/README.md)
4. [제출 보고서와 실행 증빙 체크리스트](04_Features/README.md)
5. [기존 문서·실행 결과 위치와 재사용 주의점](05_Decisions/README.md)
6. [현재 인수인계](07_Handoffs/00_Latest_Handoff.md)
7. [개발 세션에 전달할 작업 지침](08_AI_Workflow/README.md)

## 오늘 팀에 먼저 공유할 내용

현재 구현은 기술 조사 이후 시장·이해관계자·도메인 Agent를 항상 실행하는 고정 Fan-out이다. 이번 과제는 Supervisor 또는 Orchestrator-Workers 중 하나를 실제로 구현하고 동적 동작을 LangSmith로 보여주는 과제다. 보고서 생성 뒤 품질 평가와 실패 시 Loop도 반드시 필요하다.

기존 네 관점을 유지하면서 누락·근거 부족에 따라 필요한 Agent를 선택하는 Supervisor를 추천한다. 팀에서 패턴을 확정한 뒤 `State`와 Agent 입력·출력 계약부터 합의하면 각자 구현을 병렬로 진행할 수 있다. 이름별 분담은 기존 커밋 역할을 반영한 제안이며, 이번 작업을 이미 수행했다는 뜻이 아니다.

## 완료 기준

- [ ] State에 따라 `add_conditional_edges`로 하위 Agent 선택
- [ ] 각 하위 Agent는 Supervisor로 결과를 반환; 직접 Agent 간 호출 없음
- [ ] 근거 충분성 확인 후 종합·보고서 작성
- [ ] 부족한 관점만 재작업하며 이전 피드백을 질의에 반영
- [ ] 보고서 생성 후 Groundedness·중립성·편향 통제·관점 커버리지 평가
- [ ] 평가 미달 시 보완 Loop; 소진 시 실패를 명시하고 종료
- [ ] State 설계 7항목을 README에서 설명
- [ ] 실제 LangSmith trace와 코드·보고서가 동일 run에 연결
- [ ] SUMMARY와 REFERENCE가 있는 평가 보고서 PDF 10쪽 이하
- [ ] 별도 Git branch, README, Contributors 실제 기여, tracing PNG, 제출 ZIP

마감은 지침에 적힌 **DAY 2 퇴근 전**이다. 정확한 제출 시각은 반별 안내를 따른다. 점수나 실제 실행 성공은 현재 확정하지 않는다.
