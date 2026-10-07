"""비-LLM 로직에 대한 최소 self-check. pytest 없이 `python tests/test_smoke.py`로 실행."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.synthesis import has_usable_analysis, validation_judge
from app import validate_report
from evidence import format_references, make_evidence_id
from rag import _rerank, split_text
from graph import (
    build_graph,
    fan_out_or_warn,
    initial_state,
    _task_plan,
    quality_evaluator_node,
    route_after_quality,
    route_after_validation,
)


def test_split_text_respects_max_chars():
    text = "가" * 3000
    chunks = split_text(text, max_chars=1400, overlap=150)
    assert all(len(c) <= 1400 for c in chunks)
    assert "".join(chunks).replace("", "") != ""  # non-empty


def test_split_text_short_text_returns_single_chunk():
    assert split_text("짧은 문장") == ["짧은 문장"]


def test_rerank_preserves_relevant_lexical_match():
    results = [
        {"chunk_id": "semantic", "text": "attention memory architecture", "similarity": 0.9},
        {"chunk_id": "exact", "text": "reduce KV cache key value elements", "similarity": 0.8},
    ]
    reranked = _rerank("reduce KV cache", results, top_k=2)
    assert reranked[0]["chunk_id"] == "exact"


def test_make_evidence_id_is_deterministic():
    a = make_evidence_id("rag", "agent|chunk|query")
    b = make_evidence_id("rag", "agent|chunk|query")
    assert a == b
    assert a.startswith("rag-")


def test_validation_rejects_parse_error_result():
    assert not has_usable_analysis({"parse_error": True})
    assert not has_usable_analysis({"software": {"principle": ""}})


def test_empty_reference_filter_stays_empty():
    references = [{"evidence_id": "rag-aaaaaaaaaaaa", "source_type": "paper", "title": "x"}]
    assert format_references(references, used_ids=set()) == "- 실제 활용 자료 없음"


def test_web_reference_shows_unknown_date():
    references = [{
        "evidence_id": "web-aaaaaaaaaaaa",
        "source_type": "web",
        "title": "Example",
        "url": "https://example.com/article",
    }]
    assert "example.com(날짜 미상). Example" in format_references(references)


def test_malformed_evidence_id_is_ignored():
    state = {
        "technical_analysis": {"software": {"principle": "ok"}},
        "trl_analysis": {"software": {"reason": "ok"}},
        "market_analysis": {"software": {"evidence_ids": ["web-ITME-1"]}},
        "stakeholder_analysis": {"cloud_provider": {"expectation": "ok"}},
        "domain_analysis": {"comparison": "ok"},
        "synthesis": {"summary": "ok"},
        "references": [{"evidence_id": "rag-aaaaaaaaaaaa"}],
        "retry_count": 0,
    }
    result = validation_judge(state)
    assert result["validation_result"] == "pass"
    assert result["retry_count"] == 0


def test_report_requires_submission_headings():
    report = "\n\n".join([
        "# SUMMARY", "# 1. 분석 배경", "# 2. 기술 선정", "# 3. 기술 개요",
        "# 4. 관점별 평가", "# 6. 시사점", "# 7. 분석의 한계",
        "# REFERENCE", "- [rag-aaaaaaaaaaaa] Paper",
    ])
    validate_report(report)


def test_report_rejects_empty_references():
    report = "\n\n".join([
        "# SUMMARY", "# 1. 분석 배경", "# 2. 기술 선정", "# 3. 기술 개요",
        "# 4. 관점별 평가", "# 6. 시사점", "# 7. 분석의 한계", "# REFERENCE",
    ])
    try:
        validate_report(report)
    except ValueError:
        return
    raise AssertionError("빈 REFERENCE가 통과했습니다.")


def test_graph_builds_with_all_nodes_wired():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    expected = {
        "__start__", "__end__", "technology_selection", "orchestrator_plan",
        "worker", "synthesis", "validation", "report_generation",
        "quality_evaluator", "warning",
    }
    assert expected.issubset(node_names), node_names


def test_dynamic_plan_changes_with_requested_perspectives():
    state = initial_state()
    state["selected_technologies"] = {
        "software": {"name": "DeepSeek-V2 MLA"},
        "hardware": {"name": "ITME"},
    }
    plans = []
    for request in (
        "기술 성숙도와 도메인 적용성을 평가하라.",
        "기술 성숙도, 시장성과 도메인 적용성을 평가하라.",
        "기술 성숙도, 시장성, 이해관계자, 도메인 적용성을 평가하라.",
    ):
        state["input_request"] = request
        plan = _task_plan(state)
        state["plan"] = plan
        plans.append(plan)
        sends = fan_out_or_warn(state)
        assert len(sends) == len(plan)
        assert {send.node for send in sends} == {"worker"}
    assert [len(plan) for plan in plans] == [2, 3, 4]


def test_initial_state_accepts_runtime_request():
    state = initial_state("시장성과 도메인 적용성만 비교하라.")
    assert state["input_request"] == "시장성과 도메인 적용성만 비교하라."


def test_quality_evaluator_requires_grounded_and_diverse_evidence():
    state = {
        "report": "# SUMMARY\n# 1. 분석 배경\n# 2. 기술 선정\n# 3. 기술 개요\n# 4. 관점별 평가\n# 6. 시사점\n# 7. 분석의 한계\n# REFERENCE",
        "references": [{"evidence_id": "rag-aaaaaaaaaaaa", "file_name": "same.pdf", "title": "same"}],
        "technical_analysis": {"software": {"evidence_ids": ["rag-aaaaaaaaaaaa"]}},
        "trl_analysis": {"software": {"evidence_ids": ["rag-aaaaaaaaaaaa"]}},
        "market_analysis": {"software": {"evidence_ids": ["rag-aaaaaaaaaaaa"]}},
        "stakeholder_analysis": {"software": {"evidence_ids": ["rag-aaaaaaaaaaaa"]}},
        "domain_analysis": {"software": {"evidence_ids": ["rag-aaaaaaaaaaaa"]}},
        "synthesis": {"summary": "근거 기반 요약"},
        "retry_count": 0,
    }
    result = quality_evaluator_node(state)
    assert result["quality_evaluation"]["criteria"]["groundedness"] is True
    assert result["quality_evaluation"]["criteria"]["bias_control"] is False
    assert "bias_control" in result["quality_evaluation"]["issues"]


def test_quality_evaluator_rejects_empty_grounding_and_recommendation_language():
    state = {
        "report": "# SUMMARY\nMLA가 가장 우수하다.\n# 1. 분석 배경\n# 2. 기술 선정\n# 3. 기술 개요\n# 4. 관점별 평가\n# 6. 시사점\n# 7. 분석의 한계\n# REFERENCE",
        "references": [{"evidence_id": "rag-aaaaaaaaaaaa", "file_name": "paper.pdf", "title": "paper"}],
        "technical_analysis": {"software": {"principle": "근거 없는 주장"}},
        "trl_analysis": {"software": {"reason": "근거 없는 주장"}},
        "market_analysis": {"software": {"analysis": "근거 없는 주장"}},
        "stakeholder_analysis": {"software": {"analysis": "근거 없는 주장"}},
        "domain_analysis": {"software": {"analysis": "근거 없는 주장"}},
        "synthesis": {"summary": "근거 없는 요약"},
        "retry_count": 0,
    }
    result = quality_evaluator_node(state)
    criteria = result["quality_evaluation"]["criteria"]
    assert criteria["groundedness"] is False
    assert criteria["neutrality"] is False


def test_validation_can_retry_synthesis_without_unknown_worker_task():
    assert route_after_validation({"validation_result": "retry", "retry_targets": ["synthesis"]}) == "synthesis"


def test_quality_report_retry_routes_to_report_generation():
    state = {"quality_evaluation": {"result": "report_retry"}}
    assert route_after_quality(state) == "report_retry"


if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"OK: {test.__name__}")
    print(f"\n{len(tests)} smoke tests passed")
