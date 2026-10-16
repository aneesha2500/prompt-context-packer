"""The prompt-packing instances (data/queries.json) and the three tools.

A query's budget for the whole prompt is the prompt's base tokens at the skill level (no
examples) plus the query's example budget, so the room left for examples is the same at every
level. A selection is allowed when its ids are distinct candidates, every one has similarity at
least min_similarity, and base + its blocks' tokens fit the budget. The best selection maximises
the sum of similarities (compared in thousandths, as they are given to 3 decimals).
"""

from __future__ import annotations

import itertools
import json
from functools import cache
from pathlib import Path

from contract import (
    BestOutput,
    Candidate,
    CandidatesOutput,
    PackInput,
    RenderInput,
    RenderOutput,
    ScoredCandidate,
    SkillLevel,
)
from plugin.prompting import count_tokens, example_block, render

DATA = Path(__file__).with_name("data") / "queries.json"


@cache
def queries() -> dict[str, dict]:
    return {q["query_id"]: q for q in json.loads(DATA.read_text(encoding="utf-8"))["queries"]}


def query(query_id: str) -> dict:
    if query_id not in queries():
        raise ValueError(f"unknown query_id {query_id!r}; ids run q01 to q{len(queries()):02d}")
    return queries()[query_id]


def block(candidate: dict, index: int = 1) -> str:
    c = candidate
    return example_block(index, c["example_id"], c["similarity"], c["description"], c["code"])


def base_tokens(q: dict, level: SkillLevel) -> int:
    return count_tokens(render(level, q["student_code"], []))


def budget(q: dict, level: SkillLevel) -> int:
    return base_tokens(q, level) + q["example_budget"]


def milli(similarity: float) -> int:
    return round(similarity * 1000)


def list_candidates(given: PackInput, workspace: Path) -> CandidatesOutput:
    q = query(given.query_id)
    return CandidatesOutput(
        query_id=q["query_id"],
        skill_level=given.skill_level,
        student_code=q["student_code"],
        budget_tokens=budget(q, given.skill_level),
        base_tokens=base_tokens(q, given.skill_level),
        min_similarity=q["min_similarity"],
        candidates=[
            Candidate(example_id=c["example_id"], description=c["description"], similarity=c["similarity"],
                      tokens=count_tokens(block(c)))
            for c in q["candidates"]
        ],
    )


def prompt_path(query_id: str, level: SkillLevel) -> str:
    return f"prompts/{query_id}-{level.value}.md"


def render_prompt(given: RenderInput, workspace: Path) -> RenderOutput:
    """Write the prompt with the given examples, in the given order, and report its size."""
    q = query(given.query_id)
    by_id = {c["example_id"]: c for c in q["candidates"]}
    if len(set(given.example_ids)) != len(given.example_ids):
        raise ValueError("example_ids must be distinct")
    unknown = [i for i in given.example_ids if i not in by_id]
    if unknown:
        raise ValueError(f"not candidates of {given.query_id}: {unknown}")
    chosen = [by_id[i] for i in given.example_ids]
    text = render(given.skill_level, q["student_code"], [block(c, n) for n, c in enumerate(chosen, 1)])
    relative = prompt_path(q["query_id"], given.skill_level)
    path = workspace / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    total, limit = count_tokens(text), budget(q, given.skill_level)
    return RenderOutput(
        query_id=q["query_id"],
        skill_level=given.skill_level,
        path=relative,
        example_ids=list(given.example_ids),
        total_tokens=total,
        budget_tokens=limit,
        within_budget=total <= limit,
        similarity_sum=sum(milli(c["similarity"]) for c in chosen) / 1000,
    )


def best_selection(given: PackInput, workspace: Path) -> BestOutput:
    """The pack-context reference: every candidate scored, and the best allowed selection (exhaustive)."""
    q = query(given.query_id)
    level = given.skill_level
    scored = [(c, count_tokens(block(c))) for c in q["candidates"]]
    allowed = [(c, t) for c, t in scored if c["similarity"] >= q["min_similarity"]]
    room = q["example_budget"]
    best_value, best = -1, ()
    for size in range(len(allowed) + 1):
        for subset in itertools.combinations(allowed, size):
            if sum(t for _, t in subset) <= room:
                value = sum(milli(c["similarity"]) for c, _ in subset)
                if value > best_value:
                    best_value, best = value, subset
    order = sorted(best, key=lambda pair: (-pair[0]["similarity"], pair[0]["example_id"]))
    return BestOutput(
        query_id=q["query_id"],
        skill_level=level,
        student_code=q["student_code"],
        budget_tokens=budget(q, level),
        base_tokens=base_tokens(q, level),
        min_similarity=q["min_similarity"],
        candidates=[ScoredCandidate(example_id=c["example_id"], similarity=c["similarity"], tokens=t) for c, t in scored],
        optimum_similarity_sum=best_value / 1000,
        optimum_example_ids=[c["example_id"] for c, _ in order],
    )
