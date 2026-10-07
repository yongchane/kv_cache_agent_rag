"""추적 설정 확인·fixture 실행·실제 현재 Graph 실행 진입점."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="키의 값 없이 설정 유무만 확인")
    parser.add_argument("--fixture", action="store_true", help="실제 서비스와 구분되는 검증용 Graph 실행")
    parser.add_argument("--scenario", choices=["normal", "retry", "exhaust"], default="normal")
    parser.add_argument("--task-count", type=int, choices=[1, 2], default=2)
    parser.add_argument("--langsmith", action="store_true", help="원격 trace 전송·서버에서 run 존재 확인")
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    if args.langsmith:
        os.environ["LANGSMITH_TRACING"] = "true"
    if args.check:
        from observability import tracing_enabled
        print(json.dumps({
            "openai_key_configured": bool(os.getenv("OPENAI_API_KEY")),
            "langsmith_key_configured": bool(os.getenv("LANGSMITH_API_KEY")),
            "langsmith_tracing_enabled": tracing_enabled(),
            "langsmith_project": os.getenv("LANGSMITH_PROJECT", "kv-cache-agent-orchestration"),
        }, ensure_ascii=False, indent=2))
        return 0
    if args.langsmith and not os.getenv("LANGSMITH_API_KEY", "").strip():
        parser.error("LANGSMITH_API_KEY를 로컬 .env에 먼저 설정하세요.")
    if args.fixture:
        from observability import TraceSession
        from tests.fixtures.orchestration import build_fixture_graph
        session = TraceSession(ROOT / "outputs/traces", pattern="orchestrator_workers_fixture", fixture=True)
        result = session.invoke(build_fixture_graph(), {
            "task_count": args.task_count, "scenario": args.scenario, "worker_results": [], "round": 0,
        }, remote=args.langsmith)
        print("FIXTURE ONLY — 제출용 기술평가 보고서나 팀 최종 Graph 실행이 아닙니다.")
        print("상태:", result["status"], "manifest:", session.manifest_path)
        print("LangSmith 서버 확인:", session.manifest["langsmith_verified"])
        if args.langsmith and not session.manifest["langsmith_verified"]:
            return 2
        return 0 if result["status"] == "completed" else 1
    if Path.cwd().resolve() != ROOT:
        parser.error("실제 실행은 프로젝트 루트에서 진행하세요.")
    from app import run_pipeline, save_outputs
    result = run_pipeline()
    save_outputs(result)
    print("Trace manifest:", result["runtime_metadata"]["trace_manifest"])
    return 2 if args.langsmith and not result["runtime_metadata"]["langsmith_verified"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
