"""외부 LLM·검색 없이 도메인 Worker의 계약과 실패 동작을 검증한다."""
from __future__ import annotations

import unittest

from agents.domain_evaluation import evaluate_domain_task


class DomainWorkerTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.prompts = []
        self.task = {
            "task_id": "domain-hbm", "technologies": ["DeepSeek-V2 MLA", "ITME"],
            "criteria": ["HBM memory usage"], "domain": "데이터센터 LLM 서빙",
            "feedback": "실험 환경과 비교 조건을 추가 확인", "queries": ["HBM baseline conditions"],
            "attempt": 2,
        }

    def retrieve(self, query, technology, agent, top_k):
        self.calls.append((query, technology))
        suffix = "a" if technology == "DeepSeek-V2 MLA" else "b"
        return [{"evidence_id": "rag-" + suffix * 12, "technology": technology,
                 "evidence_text": "fixture only", "title": "Test paper"}]

    def response(self, system, prompt):
        self.prompts.append(prompt)
        return {"assessments": [
            {"technology": tech, "criterion": "HBM memory usage", "summary": "테스트 분석",
             "evidence_ids": ["rag-" + suffix * 12], "limitations": "조건이 다름",
             "evaluation_conditions": "논문별 조건", "information_available": True}
            for tech, suffix in [("DeepSeek-V2 MLA", "a"), ("ITME", "b")]
        ], "comparison": "직접 우열 비교하지 않음"}

    def run_task(self, generate=None, retrieve=None, task=None):
        return evaluate_domain_task(
            task or self.task, retrieve_fn=retrieve or self.retrieve,
            generate_fn=generate or self.response, format_evidence_fn=lambda x: str(x),
        )

    def test_task_criteria_queries_and_feedback_are_used(self):
        result = self.run_task()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task_id"], "domain-hbm")
        self.assertEqual(result["attempt"], 2)
        self.assertEqual(len(self.calls), 4)
        self.assertTrue(all("데이터센터 LLM 서빙" in q for q, _ in self.calls))
        self.assertIn("실험 환경과 비교 조건을 추가 확인", self.prompts[0])
        self.assertTrue(any("HBM baseline conditions" in q for q, _ in self.calls))

    def test_empty_evidence_returns_insufficient_without_llm(self):
        def forbidden(*args):
            raise AssertionError("근거가 없는데 LLM 호출")
        result = self.run_task(generate=forbidden, retrieve=lambda *a, **k: [])
        self.assertEqual(result["status"], "insufficient")
        self.assertTrue(result["gaps"])

    def test_unknown_or_cross_technology_citation_is_not_success(self):
        def wrong(system, prompt):
            response = self.response(system, prompt)
            response["assessments"][0]["evidence_ids"] = ["rag-" + "b" * 12]
            return response
        result = self.run_task(generate=wrong)
        self.assertEqual(result["status"], "insufficient")
        self.assertTrue(any("근거" in x for x in result["gaps"]))

    def test_missing_criterion_is_not_success(self):
        def missing(system, prompt):
            response = self.response(system, prompt)
            response["assessments"] = response["assessments"][:1]
            return response
        self.assertEqual(self.run_task(generate=missing)["status"], "insufficient")

    def test_parse_error_is_error(self):
        result = self.run_task(generate=lambda *a: {"parse_error": True})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "invalid_model_output")

    def test_retrieval_exception_returns_error_without_raw_credentials(self):
        def failed(*a, **kw):
            raise RuntimeError("private api credential")
        result = self.run_task(retrieve=failed)
        self.assertEqual(result["status"], "error")
        self.assertNotIn("private api credential", str(result))

    def test_invalid_criterion_rejected_before_search(self):
        task = {**self.task, "criteria": ["invented metric"]}
        self.assertEqual(self.run_task(task=task)["status"], "error")
        self.assertEqual(self.calls, [])

    def test_single_technology_task_requests_only_that_technology(self):
        def single(system, prompt):
            response = self.response(system, prompt)
            response["assessments"] = response["assessments"][:1]
            return response
        result = self.run_task(task={**self.task, "technologies": ["DeepSeek-V2 MLA"]}, generate=single)
        self.assertEqual(result["status"], "success")
        self.assertTrue(all(t == "DeepSeek-V2 MLA" for _, t in self.calls))


if __name__ == "__main__":
    unittest.main()
