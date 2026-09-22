"""Retriever 평가: Hit@K, MRR 및 질문별 검색 결과 상세 정보."""
from __future__ import annotations

from rag import build_index, download_papers, load_and_chunk_papers, retrieve

# 현용찬: 평가표의 RAG 품질 검증을 위해 질문별 정답 청크를 직접 등록한다.
# 청크 크기나 임베딩 모델을 바꾸면 이 정답 ID도 다시 확인해야 한다.
EVAL_SET = [
    {
        "id": "mla-core-mechanism",
        "question": "How does DeepSeek-V2 MLA represent keys and values to reduce KV cache?",
        "technology": "DeepSeek-V2 MLA",
        "ground_truth_chunk_ids": ["a9b797947a55c2abffb5", "a0c0c90446dbc74b4f11"],
    },
    {
        "id": "mla-memory-reduction",
        "question": "What KV cache reduction is reported for DeepSeek-V2 MLA and under what comparison?",
        "technology": "DeepSeek-V2 MLA",
        "ground_truth_chunk_ids": ["eee163f1c91fd182fd1f", "430a45f2bcbca3af0d5e"],
    },
    {
        "id": "mla-limitations",
        "question": "What deployment or architecture constraints does DeepSeek-V2 MLA have?",
        "technology": "DeepSeek-V2 MLA",
        "ground_truth_chunk_ids": ["0f3bcc79fea662df66d5", "860fef559d533ffddc42"],
    },
    {
        "id": "mla-long-context",
        "question": "What does the DeepSeek-V2 paper report about long-context efficiency or context length?",
        "technology": "DeepSeek-V2 MLA",
        "ground_truth_chunk_ids": ["a6d0dec26c6f3b97981a", "793419bcadda5a8e1753"],
    },
    {
        "id": "mla-readiness",
        "question": "What evidence in DeepSeek-V2 indicates system-scale evaluation or technology readiness?",
        "technology": "DeepSeek-V2 MLA",
        "ground_truth_chunk_ids": ["82bc570c6dce4e06ce58", "8ca8829261cd80970d61"],
    },
    {
        "id": "itme-core-mechanism",
        "question": "How does ITME use disaggregated CXL-Hybrid Memory for LLM inference?",
        "technology": "ITME",
        "ground_truth_chunk_ids": ["93a4b64e9a64ed1a9e42", "c628372184a2fb491e5a"],
    },
    {
        "id": "itme-tiering",
        "question": "What data placement or tiering strategy does ITME describe for KV cache?",
        "technology": "ITME",
        "ground_truth_chunk_ids": ["629461a39f68d526d8bf", "fc003c5cc1c3cb5fa6cf"],
    },
    {
        "id": "itme-latency",
        "question": "What latency or data-transfer trade-offs are reported for ITME?",
        "technology": "ITME",
        "ground_truth_chunk_ids": ["5c33b452f05c97f8f1c9", "c06f1ec3217b70253546"],
    },
    {
        "id": "itme-throughput",
        "question": "What throughput result and evaluation conditions are reported for ITME?",
        "technology": "ITME",
        "ground_truth_chunk_ids": ["70f14e2a229663480315", "1ed045a34e6cefa6cdce"],
    },
    {
        "id": "itme-readiness",
        "question": "What system prototype or evaluation evidence supports the readiness of ITME?",
        "technology": "ITME",
        "ground_truth_chunk_ids": ["b989221ece0c9603d8be", "22a2015fc92ce21c82d4"],
    },
]


def evaluate_retriever(eval_set: list[dict], k: int = 5) -> dict:
    if not eval_set:
        return {"message": "EVAL_SET에 검증된 정답을 입력하세요.", "evaluated": False}

    hits = 0
    reciprocal_ranks = []
    details = []

    for item in eval_set:
        # 현용찬: 상위 k개만 바로 평가하지 않고 후보를 10개까지 가져온 뒤
        # lexical rerank를 적용해 임베딩 검색과 재정렬 결과를 함께 검증한다.
        results = retrieve(
            item["question"],
            item["technology"],
            top_k=k,
            candidate_k=max(k * 2, 10),
            rerank=True,
        )
        if "ground_truth_chunk_ids" in item:
            expected = set(item["ground_truth_chunk_ids"])
            match_key = "chunk_id"
        elif "ground_truth_chunk_id" in item:
            expected = {item["ground_truth_chunk_id"]}
            match_key = "chunk_id"
        elif "expected_pages" in item:
            expected = {int(page) for page in item["expected_pages"]}
            match_key = "page"
        else:
            raise ValueError(
                f"{item.get('id', '<unknown>')}에 ground_truth_chunk_ids, ground_truth_chunk_id 또는 expected_pages가 필요합니다."
            )

        rank = None
        for index, result in enumerate(results, start=1):
            if result.get(match_key) in expected:
                rank = index
                break

        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1 / rank)
        else:
            reciprocal_ranks.append(0)

        # 현용찬: 평균 점수만으로는 실패한 질문을 확인하기 어려워
        # rank와 검색된 청크 목록을 질문별로 남긴다.
        details.append({
            "id": item.get("id"),
            "technology": item.get("technology"),
            "rank": rank,
            "matched_chunk_id": results[rank - 1].get("chunk_id") if rank else None,
            "retrieved_chunk_ids": [
                result.get("chunk_id") for result in results if result.get("chunk_id")
            ],
        })

    return {
        f"Hit@{k}": hits / len(eval_set),
        "MRR": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "questions": len(eval_set),
        "evaluated": True,
        "details": details,
    }


if __name__ == "__main__":
    # 현용찬: 평가 실행마다 문서와 색인을 다시 준비해 청킹·임베딩 설정이
    # 바뀐 뒤에도 오래된 색인으로 잘못 평가하지 않도록 한다.
    download_papers()
    chunks = load_and_chunk_papers()
    collection = build_index(chunks)
    print(f"평가용 색인 완료: 청크 {collection.count():,}개")
    print(evaluate_retriever(EVAL_SET, k=5))
