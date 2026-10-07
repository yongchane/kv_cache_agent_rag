"""실제 LangGraph Send와 도메인 Worker의 연결을 fixture로 검증한다."""
import json
import tempfile
import unittest
from pathlib import Path

from observability import TraceSession
from tests.fixtures.orchestration import build_fixture_graph


class OrchestrationContractTests(unittest.TestCase):
    def run_case(self, count, scenario):
        with tempfile.TemporaryDirectory() as directory:
            session = TraceSession(Path(directory), pattern="orchestrator_workers_fixture", fixture=True)
            result = session.invoke(build_fixture_graph(), {
                "task_count": count, "scenario": scenario, "worker_results": [], "round": 0,
            }, remote=False)
            events = [json.loads(line) for line in session.events_path.read_text().splitlines()]
            return result, events

    def test_input_changes_actual_worker_count(self):
        for count in (1, 2):
            result, events = self.run_case(count, "normal")
            workers = [e for e in events if e["event"] == "node_end" and e["node"] == "domain_worker"]
            self.assertEqual(len(workers), count)
            self.assertEqual(len(result["worker_results"]), count)
            self.assertEqual(result["status"], "completed")

    def test_retry_only_failed_task_and_preserve_other_result(self):
        result, events = self.run_case(2, "retry")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["round"], 2)
        by_id = {r["task_id"]: r for r in result["worker_results"]}
        self.assertEqual(by_id["fixture-0"]["attempt"], 2)
        self.assertEqual(by_id["fixture-1"]["attempt"], 1)
        self.assertEqual(sum(e["event"] == "node_end" and e["node"] == "domain_worker" for e in events), 3)

    def test_permanent_failure_stops_without_passing_quality(self):
        result, events = self.run_case(2, "exhaust")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["round"], 2)
        self.assertFalse(result["quality_verdict"]["passed"])


if __name__ == "__main__":
    unittest.main()
