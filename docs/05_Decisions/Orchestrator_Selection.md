# Orchestrator-Workers를 선택하고 강화하는 이유

기준: 사용자에게 전달받은 팀 결정과 역할표, 기존 `graph.py`·관점 Agent·보고서 코드, Multi-Agent Orchestration 과제 지침. 아래 이유는 코드와 요구사항을 바탕으로 정리한 해석이다. 팀 회의에서 실제로 발언한 내용을 재현한 문서는 아니다.

## 선택 이유

기존 프로젝트는 같은 기술을 시장성·이해관계자·도메인 등 여러 관점에서 독립적으로 조사하고, 종합 Agent가 하나의 보고서로 합친다. `graph.py`는 기술 조사 뒤 세 관점으로 Fan-out하고 모두 끝나면 synthesis로 Fan-in한다. `agents/`도 역할별로 분리돼 있어 Worker로 재사용하기 쉽다.

| 기존 특성 | Orchestrator-Workers와 맞는 이유 |
|---|---|
| 독립적인 관점별 조사 | 여러 Worker에게 병렬로 맡기기 적합 |
| 기술·관점·평가 기준을 나눌 수 있음 | 계획에서 조사 task를 구조화할 수 있음 |
| 종합·보고서 담당이 분리돼 있음 | Worker 결과를 Synthesizer가 집계하는 구조 재사용 |
| PDF RAG와 웹 검색의 역할이 다름 | task 종류에 맞는 Worker·근거 수집 경로 선택 가능 |
| 팀원별 Agent 파일 분리 | 공통 계약에 맞춰 병렬 개발하기 수월 |

병렬 처리로 전체 조사 대기 시간을 줄일 가능성이 있지만 실제 속도 개선 수치는 측정 전에는 주장하지 않는다. 독립적이지 않은 작업은 계획 단계에서 선후 관계를 반영해야 한다.

## 강화 이유

기존 흐름은 고정 병렬 workflow다. 기존 코드가 이미 과제의 완성된 Orchestrator-Workers를 구현했다는 뜻은 아니다.

| 현재 제약 | 강화 방향 | 과제와 연결 |
|---|---|---|
| 매번 같은 세 Agent 실행 | 입력과 부족 항목에 따른 task 계획 생성·State 저장 | 패턴 적용·동적 동작 |
| 고정 Graph edge로 Fan-out | 계획 이후 `Send` 등으로 Worker 실행 결정 | Dynamic Fan-out 필수 |
| 실패하면 전체 조사 반복 | 실패 task만 재시도, 완료 task 보존, 소진 시 제외/중단 정책 | fallback 필수 |
| 느슨한 dict 결과 | task_id·기술·기준·상태·근거·시도 횟수 계약 | State 설계 |
| 보고서 생성 뒤 END | 생성 후 품질 평가와 실패 Loop | 품질 노드 15점 |
| 설계 그림만으로 동작 설명 | 실제 실행에서 작업 수·재시도·품질 Loop trace 확보 | 동적 실증 20점 |

목표는 **필요한 조사 작업을 계획하고 병렬 수행하며, 실패·근거 부족·보고서 품질을 확인해 보완하는 구조**다. 특정 패턴 이름을 바꾸는 것으로 완료되지 않는다.

## 이번 현용찬 작업의 범위

도메인 Worker를 task 입력 방식으로 만들고, 기존 Graph와 새 Graph 양쪽에서 사용할 추적 실행기를 추가했다. 테스트용 Orchestrator로 dynamic fan-out과 fallback의 Worker 계약을 검증했다. 팀 production의 계획·State·reducer는 임유리 담당, Synthesizer·보고서·품질 Loop는 김선정 담당이며 원격 코드 통합 후 다시 검증해야 한다.
