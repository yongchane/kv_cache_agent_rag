"""실제 LangGraph의 callback 실행과 로컬 증빙을 검증한다. 외부 전송 없음."""
import json
import tempfile
import unittest
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from observability import TraceSession


class DemoState(TypedDict):
    report: str
    quality_verdict: dict


class TracingTests(unittest.TestCase):
    def test_real_graph_records_nodes_and_quality_without_full_report(self):
        builder = StateGraph(DemoState)
        builder.add_node("report", lambda state: {"report": "private report body"})
        builder.add_node("quality", lambda state: {"quality_verdict": {"passed": True}})
        builder.add_edge(START, "report")
        builder.add_edge("report", "quality")
        builder.add_edge("quality", END)
        with tempfile.TemporaryDirectory() as directory:
            session = TraceSession(Path(directory), pattern="test_fixture", fixture=True)
            result = session.invoke(builder.compile(), {}, remote=False)
            self.assertTrue(result["quality_verdict"]["passed"])
            events_text = session.events_path.read_text()
            events = [json.loads(line) for line in events_text.splitlines()]
            ended = [e for e in events if e["event"] == "node_end"]
            self.assertIn("quality", {e["node"] for e in ended})
            self.assertNotIn("private report body", events_text)
            manifest = json.loads(session.manifest_path.read_text())
            self.assertEqual(manifest["status"], "completed")
            self.assertTrue(manifest["fixture"])
            self.assertFalse(manifest["langsmith_verified"])
            self.assertTrue(all(e["trace_id"] == manifest["trace_id"] for e in events))

    def test_failed_graph_keeps_failure_manifest_without_raw_error(self):
        builder = StateGraph(DemoState)
        def fail(state):
            raise RuntimeError("sensitive request")
        builder.add_node("fail", fail)
        builder.add_edge(START, "fail")
        builder.add_edge("fail", END)
        with tempfile.TemporaryDirectory() as directory:
            session = TraceSession(Path(directory), fixture=True)
            with self.assertRaises(RuntimeError):
                session.invoke(builder.compile(), {}, remote=False)
            manifest = json.loads(session.manifest_path.read_text())
            self.assertEqual(manifest["status"], "error")
            self.assertEqual(manifest["error_type"], "RuntimeError")
            self.assertNotIn("sensitive request", session.events_path.read_text())

    def test_remote_requested_without_key_fails_before_graph_execution(self):
        from unittest.mock import patch, Mock
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"LANGSMITH_API_KEY": ""}):
            graph = Mock()
            session = TraceSession(Path(directory))
            with self.assertRaisesRegex(RuntimeError, "LANGSMITH_API_KEY"):
                session.invoke(graph, {}, remote=True)
            graph.invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
