"""실제 논문 검색·LLM으로 한 기준만 평가하는 제한적 smoke 실행."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from langgraph.graph import END, START, StateGraph
    from agents.domain_evaluation import evaluate_domain_task
    from observability import TraceSession

    class SmokeState(TypedDict, total=False):
        task: dict
        task_id: str
        view: str
        attempt: int
        status: str
        analysis: dict
        references: list
        gaps: list
        error: str | None

    if Path.cwd().resolve() != ROOT:
        raise SystemExit("프로젝트 루트에서 실행하세요.")
    graph = StateGraph(SmokeState)
    graph.add_node("domain_worker", lambda state: evaluate_domain_task(state["task"]))
    graph.add_edge(START, "domain_worker")
    graph.add_edge("domain_worker", END)
    session = TraceSession(ROOT / "outputs/traces", pattern="domain_worker_smoke", fixture=False)
    result = session.invoke(graph.compile(), {"task": {
        "task_id": "live-domain-hbm", "criteria": ["HBM memory usage"], "top_k": 2,
        "feedback": "논문에서 확인할 수 있는 비교 조건과 한계를 명시",
    }})
    output = session.directory / "domain_result.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    session.attach_artifacts({"domain_result": output})
    print("실제 도메인 1개 기준 smoke; 전체 보고서·팀 Orchestrator 검증이 아닙니다.")
    print("status:", result["status"], "evidence:", len(result["references"]), "error:", result["error"])
    print("manifest:", session.manifest_path)
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
