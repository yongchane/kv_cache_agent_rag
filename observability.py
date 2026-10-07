"""Graph 실행을 로컬 JSONL과 LangSmith로 추적한다."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langsmith import Client, tracing_context


def tracing_enabled() -> bool:
    return os.getenv("LANGSMITH_TRACING", "false").strip().lower() in {"true", "1", "yes", "on"}


def control_summary(value) -> dict:
    """로컬 event에는 제어 요약만 남기며 전체 프롬프트·보고서는 복사하지 않는다."""
    if not isinstance(value, dict):
        return {}
    summary = {}
    for key in ("task_id", "view", "attempt", "status", "retry_count", "validation_result", "next_action"):
        if key in value and isinstance(value[key], (str, int, bool)):
            summary[key] = value[key]
    for key in ("tasks", "plan", "worker_results", "results", "references", "errors", "gaps"):
        if isinstance(value.get(key), list):
            summary[key + "_count"] = len(value[key])
    if isinstance(value.get("tasks"), list):
        summary["task_ids"] = [str(t.get("task_id", "unknown"))[:100] for t in value["tasks"][:50] if isinstance(t, dict)]
    if isinstance(value.get("task"), dict):
        summary["task"] = control_summary(value["task"])
    if isinstance(value.get("worker_results"), list):
        summary["worker_outcomes"] = [control_summary(item) for item in value["worker_results"][:50]]
    for key in ("quality_verdict", "eval_result"):
        verdict = value.get(key)
        if isinstance(verdict, dict):
            summary[key] = {k: verdict[k] for k in ("passed", "repair_action") if k in verdict}
    decision = value.get("decision")
    if isinstance(decision, dict):
        summary["decision"] = {k: str(decision[k])[:1000] for k in ("action", "reason", "target_view") if k in decision}
    if isinstance(value.get("report"), str):
        summary["report_chars"] = len(value["report"])
    return summary


class LocalTraceRecorder(BaseCallbackHandler):
    def __init__(self, path: Path, trace_id: str):
        self.path, self.trace_id = path, trace_id
        self._nodes = {}
        self._lock = Lock()

    def _write(self, event, run_id, parent_run_id=None, summary=None):
        with self._lock:
            record = {
                "event": event, "ts": datetime.now(timezone.utc).isoformat(),
                "trace_id": self.trace_id, "run_id": str(run_id),
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
                "node": self._nodes.get(str(run_id), "graph"), "summary": summary or {},
            }
            with self.path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, metadata=None, **kwargs):
        self._nodes[str(run_id)] = (metadata or {}).get("langgraph_node") or kwargs.get("name") or "graph"
        self._write("node_start", run_id, parent_run_id, control_summary(inputs))

    def on_chain_end(self, outputs, *, run_id, parent_run_id=None, **kwargs):
        self._write("node_end", run_id, parent_run_id, control_summary(outputs))

    def on_chain_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        self._write("node_error", run_id, parent_run_id, {"error_type": type(error).__name__})


class TraceSession:
    """compiled Graph의 State나 라우팅을 변경하지 않고 실행을 기록한다."""
    def __init__(self, output_dir: Path, *, pattern="baseline_static", fixture=False):
        self.run_id = uuid4()
        self.trace_id = str(self.run_id)
        self.directory = Path(output_dir) / self.trace_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.events_path = self.directory / "events.jsonl"
        self.manifest_path = self.directory / "manifest.json"
        try:
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            commit = "unknown"
        self.manifest = {
            "trace_id": self.trace_id, "langsmith_run_id": self.trace_id,
            "thread_id": self.trace_id, "git_commit": commit, "pattern": pattern,
            "fixture": fixture, "status": "prepared", "langsmith_verified": False,
            "started_at": datetime.now(timezone.utc).isoformat(), "events": str(self.events_path),
        }
        self._save()

    def _save(self):
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def invoke(self, graph, initial_state, *, remote=None, recursion_limit=40):
        remote = tracing_enabled() if remote is None else remote
        if remote and not os.getenv("LANGSMITH_API_KEY", "").strip():
            self.manifest.update(status="configuration_error", error_type="missing_langsmith_key")
            self._save()
            raise RuntimeError("LANGSMITH_API_KEY를 로컬 .env에 설정하세요.")
        project = os.getenv("LANGSMITH_PROJECT", "kv-cache-agent-orchestration")
        client = Client() if remote else None
        self.manifest.update(status="running", langsmith_requested=remote, langsmith_project=project)
        self._save()
        callback = LocalTraceRecorder(self.events_path, self.trace_id)
        try:
            with tracing_context(enabled=remote, client=client, project_name=project):
                result = graph.invoke(initial_state, config={
                    "run_id": self.run_id, "run_name": "kv-cache-evaluation",
                    "recursion_limit": recursion_limit, "callbacks": [callback],
                    "configurable": {"thread_id": self.trace_id},
                    "metadata": {"trace_id": self.trace_id, "git_commit": self.manifest["git_commit"],
                                 "pattern": self.manifest["pattern"], "fixture": self.manifest["fixture"]},
                    "tags": ["fixture" if self.manifest["fixture"] else "live"],
                })
            status = result.get("status", "completed") if isinstance(result, dict) else "completed"
            self.manifest.update(status=status, graph_status="completed", result_summary=control_summary(result))
            return result
        except Exception as error:
            self.manifest.update(status="error", error_type=type(error).__name__)
            raise
        finally:
            if client is not None:
                try:
                    client.flush()
                    run = client.read_run(self.run_id)
                    self.manifest.update(langsmith_verified=run.id == self.run_id,
                                         langsmith_url=client.get_run_url(run=run))
                except Exception as error:
                    self.manifest["trace_export_error"] = type(error).__name__
            self.manifest["ended_at"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def attach_artifacts(self, artifacts: dict):
        self.manifest["artifacts"] = {key: str(value) for key, value in artifacts.items()}
        self._save()
