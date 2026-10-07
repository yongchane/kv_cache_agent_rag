"""팀 production Graph를 실행하되 외부 검색·LLM은 mock으로 분리한다."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import graph
from agents.domain_evaluation import domain_evaluation_agent
from observability import TraceSession, control_summary


class TeamIntegrationTests(unittest.TestCase):
    def run_team(self, fail=False):
        calls = []
        refs = [{"evidence_id": "rag-" + c * 12, "file_name": c + ".pdf"}
                for c in ("a", "b")]
        analysis = {"evidence_ids": [r["evidence_id"] for r in refs]}

        def worker(state):
            task = state["current_task"]
            calls.append(dict(task))
            keys = graph.TASK_OUTPUT_KEYS[task["task_id"]]
            failed = task["task_id"] == "domain_evaluation" and (fail == "always" or fail and task["attempt"] == 1)
            result = {key: {"parse_error": True} if failed else analysis for key in keys}
            result["references"] = refs
            if failed:
                result["errors"] = ["fixture_failure"]
            return result

        selection = {"selected_technologies": {"software": {"name": "DeepSeek-V2 MLA"},
                     "hardware": {"name": "ITME"}}, "selection_reason": "fixture", "domain": "fixture"}
        report = "\n".join(graph.REQUIRED_REPORT_HEADINGS)
        with patch.dict(graph.TASK_RUNNERS, {key: worker for key in graph.TASKS}), \
             patch.object(graph, "technology_selection_agent", return_value=selection), \
             patch.object(graph, "synthesis_agent", return_value={"synthesis": analysis}), \
             patch.object(graph, "report_generation_agent", return_value={"report": report}), \
             patch.object(graph, "MAX_RETRIES", 2), \
             patch("agents.synthesis.MAX_RETRIES", 2), \
             tempfile.TemporaryDirectory() as directory:
            session = TraceSession(Path(directory), pattern="team_graph_mock", fixture=True)
            result = session.invoke(graph.build_graph(), graph.initial_state("기술 성숙도와 도메인 적용성을 평가하라."), remote=False)
            events = [json.loads(line) for line in session.events_path.read_text().splitlines()]
            self.assertEqual(result["trace_id"], session.trace_id)
            self.assertTrue(all(e["trace_id"] == result["trace_id"] for e in events))
            return result, calls, events

    def test_requested_two_views_finish_without_unrequested_workers(self):
        result, calls, events = self.run_team()
        self.assertEqual(result["status"], "success")
        self.assertEqual({c["task_id"] for c in calls}, {"technical_research", "domain_evaluation"})
        self.assertEqual(len(calls), 2)
        self.assertTrue(any(e["node"] == "quality_evaluator" for e in events))

    def test_only_failed_view_retries_and_attempt_increments(self):
        result, calls, _ = self.run_team(fail=True)
        self.assertEqual(result["status"], "success")
        domain = [c for c in calls if c["task_id"] == "domain_evaluation"]
        self.assertEqual([c["attempt"] for c in domain], [1, 2])
        self.assertTrue(domain[1]["feedback"])
        self.assertTrue(domain[1]["queries"])
        self.assertEqual(len(calls), 3)

    def test_permanent_failure_terminates_with_warning(self):
        result, calls, _ = self.run_team(fail="always")
        self.assertEqual(result["status"], "warning")
        self.assertLessEqual(result["retry_count"], 2)
        self.assertLessEqual(len(calls), 4)

    def test_domain_adapter_passes_current_task_feedback(self):
        task = {"task_id": "domain_evaluation", "attempt": 2, "feedback": "source diversity",
                "queries": ["independent evidence"], "objective": "not a DomainTask field"}
        output = {"analysis": {"ok": True}, "status": "success", "references": [], "gaps": [], "error": None}
        with patch("agents.domain_evaluation.evaluate_domain_task", return_value=output) as evaluate:
            result = domain_evaluation_agent({"current_task": task, "domain": "serving"})
            supplied = evaluate.call_args.args[0]
            self.assertEqual(supplied["attempt"], 2)
            self.assertEqual(supplied["feedback"], "source diversity")
            self.assertNotIn("objective", supplied)
            self.assertEqual(result["domain_task_result"], output)

    def test_remote_summaries_keep_control_not_prompts(self):
        summary = control_summary({"messages": [{"content": "secret"}], "report": "secret",
            "current_task": {"task_id": "domain_evaluation", "attempt": 2, "objective": "secret"},
            "quality_evaluation": {"result": "retry", "issues": ["bias_control"]},
            "task_results": [{"task_id": "domain_evaluation", "attempt": 2, "status": "failed"}]})
        self.assertNotIn("secret", json.dumps(summary))
        self.assertEqual(summary["current_task"]["attempt"], 2)
        self.assertEqual(summary["quality_evaluation"]["result"], "retry")

    def test_remote_client_uses_sanitizers_and_verifies_same_run(self):
        from contextlib import nullcontext
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict("os.environ", {"LANGSMITH_API_KEY": "test-placeholder"}), \
             patch("observability.Client") as factory, \
             patch("observability.tracing_context", return_value=nullcontext()):
            session = TraceSession(Path(directory), fixture=True)
            factory.return_value.read_run.return_value.id = session.run_id
            factory.return_value.get_run_url.return_value = "https://smith.langchain.com/mock"
            compiled = Mock()
            compiled.invoke.return_value = {"status": "success"}
            session.invoke(compiled, {"trace_id": "old-id"}, remote=True)
            self.assertIs(factory.call_args.kwargs["hide_inputs"], control_summary)
            self.assertIs(factory.call_args.kwargs["hide_outputs"], control_summary)
            self.assertEqual(compiled.invoke.call_args.args[0]["trace_id"], session.trace_id)
            self.assertTrue(session.manifest["langsmith_verified"])


if __name__ == "__main__":
    unittest.main()
