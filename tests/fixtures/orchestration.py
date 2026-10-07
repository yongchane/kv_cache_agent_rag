"""도메인 Worker 통합 검증용 Orchestrator. 팀 최종 Graph 구현이 아니다."""
from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agents.domain_evaluation import DOMAIN_TECHNOLOGIES, evaluate_domain_task


def merge_results(left, right):
    merged = {item["task_id"]: item for item in left or []}
    for item in right or []:
        merged[item["task_id"]] = item
    return list(merged.values())


class FixtureState(TypedDict, total=False):
    task_count: int
    scenario: str
    tasks: list[dict]
    worker_results: Annotated[list[dict], merge_results]
    round: int
    report: str
    quality_verdict: dict
    status: str


def build_fixture_graph():
    def orchestrator(state):
        if state.get("worker_results"):
            tasks = [{
                "task_id": r["task_id"], "technologies": [r["technology"]],
                "criteria": ["HBM memory usage"], "attempt": r["attempt"] + 1,
                "feedback": "테스트용 근거 부족 보완", "queries": ["HBM evaluation conditions"],
            } for r in state["worker_results"] if r["status"] != "success"]
        else:
            tasks = [{"task_id": f"fixture-{i}", "technologies": [technology],
                      "criteria": ["HBM memory usage"], "attempt": 1}
                     for i, technology in enumerate(DOMAIN_TECHNOLOGIES[:state["task_count"]])]
        return {"tasks": tasks, "round": state.get("round", 0) + 1}

    def dispatch(state):
        return [Send("domain_worker", {"task": task, "scenario": state["scenario"]}) for task in state["tasks"]]

    def worker(state):
        task = state["task"]
        technology = task["technologies"][0]
        evidence_id = "rag-" + ("a" if technology == DOMAIN_TECHNOLOGIES[0] else "b") * 12
        fail = task["task_id"] == "fixture-0" and (
            state["scenario"] == "exhaust" or state["scenario"] == "retry" and task["attempt"] == 1)
        def retrieve(*args, **kwargs):
            return [] if fail else [{"evidence_id": evidence_id, "technology": technology,
                                     "title": "FIXTURE", "evidence_text": "TEST DATA ONLY"}]
        def generate(*args):
            return {"assessments": [{"technology": technology, "criterion": "HBM memory usage",
                     "summary": "검증용 설명", "evidence_ids": [evidence_id], "limitations": "실제 결과 아님",
                     "evaluation_conditions": "fixture", "information_available": True}],
                    "comparison": "검증용 데이터"}
        result = evaluate_domain_task(task, retrieve_fn=retrieve, generate_fn=generate, format_evidence_fn=str)
        result["technology"] = technology
        return {"worker_results": [result]}

    def synthesize(state):
        return {"report": "FIXTURE ONLY: 실제 기술 평가 보고서가 아님"}

    def quality(state):
        passed = all(r["status"] == "success" for r in state["worker_results"])
        return {"quality_verdict": {"passed": passed},
                "status": "completed" if passed else "failed" if state["round"] >= 2 else "retry"}

    builder = StateGraph(FixtureState)
    for name, node in [("orchestrator", orchestrator), ("domain_worker", worker),
                       ("synthesizer", synthesize), ("quality", quality)]:
        builder.add_node(name, node)
    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges("orchestrator", dispatch, ["domain_worker"])
    builder.add_edge("domain_worker", "synthesizer")
    builder.add_edge("synthesizer", "quality")
    builder.add_conditional_edges("quality", lambda state: "retry" if state["status"] == "retry" else "end",
                                  {"retry": "orchestrator", "end": END})
    return builder.compile()
