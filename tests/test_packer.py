from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from contract import PackInput, RenderInput, SkillLevel
from plugin import best_selection, list_candidates, render_prompt
from plugin.packer import queries
from plugin.prompting import count_tokens


def test_tokens_add_up_block_by_block(tmp_path: Path) -> None:
    for level in SkillLevel:
        cands = list_candidates(PackInput(query_id="q05", skill_level=level), Path("."))
        ids = [c.example_id for c in cands.candidates[:3]]
        out = render_prompt(RenderInput(query_id="q05", skill_level=level, example_ids=ids), tmp_path)
        assert out.total_tokens == cands.base_tokens + sum(c.tokens for c in cands.candidates[:3])
        assert count_tokens((tmp_path / out.path).read_text()) == out.total_tokens


@pytest.mark.parametrize("query_id", sorted(queries()))
def test_the_reference_is_optimal_and_greedy_is_not(query_id: str) -> None:
    given = PackInput(query_id=query_id, skill_level=SkillLevel.INTERMEDIATE)
    cands = list_candidates(given, Path("."))
    best = best_selection(given, Path("."))
    room = cands.budget_tokens - cands.base_tokens
    allowed = [c for c in cands.candidates if c.similarity >= cands.min_similarity]
    brute = max(
        sum(round(c.similarity * 1000) for c in subset)
        for size in range(len(allowed) + 1)
        for subset in itertools.combinations(allowed, size)
        if sum(c.tokens for c in subset) <= room
    )
    assert round(best.optimum_similarity_sum * 1000) == brute
    left, greedy = room, 0
    for c in sorted(allowed, key=lambda c: (-c.similarity, c.example_id)):
        if c.tokens <= left:
            left -= c.tokens
            greedy += round(c.similarity * 1000)
    assert greedy < brute  # every instance needs more than the obvious strategy


def test_render_refuses_unknown_or_repeated_ids(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        render_prompt(RenderInput(query_id="q01", skill_level=SkillLevel.BEGINNER, example_ids=["mbpp-1"]), tmp_path)
    first = list_candidates(PackInput(query_id="q01", skill_level=SkillLevel.BEGINNER), Path(".")).candidates[0].example_id
    with pytest.raises(ValueError):
        render_prompt(RenderInput(query_id="q01", skill_level=SkillLevel.BEGINNER, example_ids=[first, first]), tmp_path)
    with pytest.raises(ValueError):
        list_candidates(PackInput(query_id="q99", skill_level=SkillLevel.BEGINNER), Path("."))
