# 기존 자료 조사와 설계 판단

## 찾은 관련 자료

| 자료 | 로컬 위치 | 이번 사용 방식 |
|---|---|---|
| 수업 개념 대응·설계서 검토 | `/Users/hyeon-yongchan/Downloads/kv_cache_agentic_rag_notebook/수업매칭_설계서검토.md` | 기존 State·Reducer·Fan-out·RAG 개념 설명 참고. 코드 기준이 9/22 초기 전달본임 |
| 개발 산출물 평가표 검증 | `/Users/hyeon-yongchan/Downloads/kv_cache_agentic_rag_notebook/개발산출물_평가표검증.md` | 이전 실패·검증 범위 참고. 이번 과제 점수표로 교체 필요 |
| 통합 실습 / 오프라인 검증 노트북 | 같은 폴더의 `KV_Cache_Agentic_RAG_통합실습.ipynb` / `KV_Cache_Agentic_RAG_통합실습_오프라인검증.ipynb` | 이전 코드 보관·학습용. 이번 과제 최신 실행 증빙으로 사용하지 않음 |
| 검증 원자료 | 같은 폴더의 `verification_results.json`, `verification_environment.txt` | 당시 mock/offline 검증과 실서비스 미검증을 구분하는 참고 |
| 이전 보고서와 State | `/Users/hyeon-yongchan/Downloads/kv_cache_agentic_rag/outputs/kv_cache_report_20260922_100831.md` 및 같은 시각 JSON·HTML | 이전 출력 목차와 품질 문제 참고; 새 기술평가 결과로 재사용하지 않음 |
| 기존 Graph 그림 | 저장소 `docs/architecture.png` | 현재 고정 Fan-out 설명용. 새 Supervisor 그림으로 별도 생성 필요 |
| 이번 실습 지침 | 사용자가 첨부한 2026-10-07 Multi-Agent Orchestration 텍스트 | 이번 요구사항·채점·제출 규칙의 기준 |

로컬 Obsidian vault에서 관련 KV cache 프로젝트 문서가 검색되지 않았다. 현재 조사 범위에서 관련 상세 자료는 Downloads와 개발 저장소에 있다. 이 사실은 다른 클라우드·장치에도 자료가 없다는 뜻이 아니다.

`Agent_설계서_양식_7반_5조.docx`와 `(2).docx`는 내용을 확인하니 **MarketRadar 뉴스 브리핑 Agent** 문서였다. 이번 KV cache 설계서로 잘못 연결하지 않는다. 기타 Agent 양식은 템플릿이며 프로젝트 실적 증거가 아니다.

## 9월 검토와 최신 main의 차이

| 이전 검토 항목 | 현재 확인 |
|---|---|
| 생성 Qwen/Ollama | `llm.py`가 OpenAI SDK, 기본 `gpt-4o-mini`; 임베딩은 Ollama 유지 |
| 1,400자/150자 청킹 | `config.py`는 900자/120자 |
| EVAL_SET 비어 있음 | `evaluate.py`에 10문항 정답 청크 등록. 실제 점수는 별도 실행 필요 |
| parse_error dict 통과 | `has_usable_analysis`에 오류·빈 하위 결과 검사 보완됨; 의미적 사실 검증은 별개 |
| 빈 인용 목록에서 전체 참고문헌 출력 | 필터 유틸 보완 흔적 있음. 현재 보고서 생성은 분석 payload의 ID를 모아 사용하므로 최종 주장 연결을 별도 확인해야 함 |
| 앞 기술의 근거가 문맥 예산 독점 | `compact_evidence`가 기술별 예산 배분·중복 제거 수행 |
| Contributors 미작성 | 최신 README에 팀원별 커밋 근거·역할 표 있음 |
| 생성 후 품질 검사 없음 | 여전히 `report_generation → END`; 이번 과제로 추가 필요 |
| 재시도 전체 조사 반복 | 여전히 `validation → technical_research`; 선택적 라우팅 필요 |

## 설계 제안의 근거

- **Supervisor 추천:** 부족 관점만 재조사하는 목적과 기존 역할별 모듈에 적합. 최대 처리속도보다 과제의 동적 판단·설명 가능한 재작업을 우선한다.
- **Hybrid Judge 추천:** 형식·ID 오류는 규칙으로 재현 가능하게 잡고, 주장-출처 관련성·중립성은 구조화 LLM 판정을 병행한다. Judge도 오류 가능성이 있어 최종 사람 검수를 둔다.
- **제한적 수정 우선:** RAG 전체를 재작성하기보다 Agent adapter와 제어 계층을 먼저 맞춰 통합 위험을 줄인다.
- **보고서 인용 유지:** 현재 숨겨진 근거 ID 방식은 Groundedness 실증에 불리해 본문 각주 또는 주장 매핑을 보존한다.

이는 팀 검토를 위한 제안이다. 최종 패턴·역할·재시도 상한은 팀 합의와 실제 구현 결과에 맞춰 갱신한다.
