from __future__ import annotations

from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import BestOutput, PackInput, PackOutput, RenderInput, RenderOutput, SkillLevel
from plugin import best_selection, list_candidates, render_prompt

QUERY, LEVEL = "q02", SkillLevel.BEGINNER


def given() -> PackInput:
    return PackInput(query_id=QUERY, skill_level=LEVEL)


def reference() -> BestOutput:
    return build_output(plain_output(best_selection(given(), Path("."))), BestOutput)


def greedy_ids() -> list[str]:
    """Most similar first, adding each example that still fits: the tempting, non-optimal strategy."""
    cands = list_candidates(given(), Path("."))
    room, chosen = cands.budget_tokens - cands.base_tokens, []
    for c in sorted(cands.candidates, key=lambda c: (-c.similarity, c.example_id)):
        if c.similarity >= cands.min_similarity and c.tokens <= room:
            chosen.append(c.example_id)
            room -= c.tokens
    return chosen


def submit(workspace: Path, ids: list[str], *, render: list[str] | None = None, **changes) -> dict:
    rendered = render_prompt(RenderInput(query_id=QUERY, skill_level=LEVEL, example_ids=render if render is not None else ids), workspace)
    output = {
        "query_id": QUERY,
        "skill_level": LEVEL.value,
        "example_ids": ids,
        "path": rendered.path,
        "total_tokens": rendered.total_tokens,
        "similarity_sum": rendered.similarity_sum,
    } | changes
    return verifier.verify_task("pack-context", given(), build_output(output, PackOutput), reference(), str(workspace))


def test_approves_the_best_selection(tmp_path: Path) -> None:
    verdict = submit(tmp_path, list(reference().optimum_example_ids))
    assert verdict["valid"] is True and verdict["score"] == 1.0


def test_greedy_is_allowed_but_not_best(tmp_path: Path) -> None:
    verdict = submit(tmp_path, greedy_ids())
    assert verdict["valid"] is False and 0.5 < verdict["score"] < 1.0
    assert "below the best" in verdict["message"]


def test_no_examples_is_allowed_with_score_zero(tmp_path: Path) -> None:
    verdict = submit(tmp_path, [])
    assert verdict["valid"] is False and verdict["score"] == 0.0


@pytest.mark.parametrize(
    ("make_ids", "problem"),
    [
        (lambda c: [x.example_id for x in c.candidates], "over the budget"),  # everything
        (lambda c: [c.candidates[-1].example_id], "below the similarity floor"),  # 0.148 < 0.15
        (lambda c: list(reversed(reference().optimum_example_ids)), "not ordered"),
    ],
)
def test_refuses_a_selection_that_breaks_a_rule(tmp_path: Path, make_ids, problem: str) -> None:
    ids = make_ids(list_candidates(given(), Path(".")))
    verdict = submit(tmp_path, ids)
    assert verdict["valid"] is False and verdict["score"] == 0.0 and problem in verdict["message"]


def test_refuses_an_unknown_or_repeated_example(tmp_path: Path) -> None:
    best = list(reference().optimum_example_ids)
    verdict = submit(tmp_path, [*best, "mbpp-1"], render=best)
    assert verdict["valid"] is False and "not candidates" in verdict["message"]
    verdict = submit(tmp_path, [best[0], best[0]], render=best)
    assert verdict["valid"] is False and "twice" in verdict["message"]


def test_refuses_a_submission_that_does_not_match_the_rendered_prompt(tmp_path: Path) -> None:
    best = list(reference().optimum_example_ids)
    # rendered one selection, submitted another
    verdict = submit(tmp_path, best, render=best[:1])
    assert verdict["valid"] is False and "rendered prompt" in verdict["message"]
    # claimed fewer tokens than the prompt has
    verdict = submit(tmp_path, best, total_tokens=10)
    assert verdict["valid"] is False and "total_tokens" in verdict["message"]
    verdict = submit(tmp_path, best, similarity_sum=9.0)
    assert verdict["valid"] is False and "similarity_sum" in verdict["message"]


def test_refuses_a_missing_prompt_file(tmp_path: Path) -> None:
    best = list(reference().optimum_example_ids)
    output = {"query_id": QUERY, "skill_level": LEVEL.value, "example_ids": best,
              "path": f"prompts/{QUERY}-beginner.md", "total_tokens": 1, "similarity_sum": 0.0}
    verdict = verifier.verify_task("pack-context", given(), build_output(output, PackOutput), reference(), str(tmp_path))
    assert verdict["valid"] is False and "render_prompt" in verdict["message"]


def test_refuses_another_query_or_level(tmp_path: Path) -> None:
    best = list(reference().optimum_example_ids)
    assert submit(tmp_path, best, query_id="q03")["valid"] is False
    assert submit(tmp_path, best, skill_level="advanced")["valid"] is False


def test_render_output_is_checked_against_the_file(tmp_path: Path) -> None:
    request = RenderInput(query_id=QUERY, skill_level=LEVEL, example_ids=greedy_ids())
    made = build_output(plain_output(render_prompt(request, tmp_path)), RenderOutput)
    assert verifier.verify_output("render_prompt", request, made, str(tmp_path))["valid"] is True
    made.total_tokens += 1
    assert verifier.verify_output("render_prompt", request, made, str(tmp_path))["valid"] is False


@pytest.mark.parametrize(("query_id", "valid"), [("q01", True), ("q10", True), ("1", False), ("q1", False), ("", False)])
def test_checks_the_query_id(query_id: str, valid: bool) -> None:
    value = build_output({"query_id": query_id, "skill_level": "beginner"}, PackInput)
    assert verifier.verify_input("list_candidates", value)["valid"] is valid
