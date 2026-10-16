"""The pack-context task's outcome check.

Against the pinned best_selection (every candidate's similarity and tokens, and the best allowed
similarity sum), the submitted selection must be allowed (known, distinct, above the similarity
floor, within the token budget), in prompt order (most similar first, ties by example_id), and
match the prompt file render_prompt wrote: that file must hold exactly these examples in this
order, the student's code, and exactly total_tokens tokens. A selection that breaks a rule scores
0. An allowed one scores its similarity sum over the best possible, and is valid only when it
reaches the best.
"""

from pathlib import Path

from .checks import count_tokens, milli, prompt_examples, prompt_path, result


def verify_task(arguments, output, reference, workspace):
    """``output``: a contract PackOutput; ``reference``: the pinned BestOutput."""
    if output.query_id != arguments.query_id or output.skill_level != arguments.skill_level:
        return result(False, "the selection is for another query or skill level", score=0.0)
    by_id = {c.example_id: c for c in reference.candidates}
    ids = list(output.example_ids)
    problems = []
    if len(set(ids)) != len(ids):
        problems.append("an example is chosen twice")
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        problems.append(f"not candidates: {unknown}")
    chosen = [by_id[i] for i in ids if i in by_id]
    below = [c.example_id for c in chosen if c.similarity < reference.min_similarity]
    if below:
        problems.append(f"below the similarity floor {reference.min_similarity}: {below}")
    total = reference.base_tokens + sum(c.tokens for c in chosen)
    if total > reference.budget_tokens:
        problems.append(f"{total} tokens is over the budget of {reference.budget_tokens}")
    if ids != [c.example_id for c in sorted(chosen, key=lambda c: (-c.similarity, c.example_id))]:
        problems.append("examples are not ordered most similar first (ties by example_id)")

    path = Path(workspace) / prompt_path(arguments.query_id, arguments.skill_level)
    if output.path != prompt_path(arguments.query_id, arguments.skill_level) or not path.is_file():
        problems.append("the prompt was not rendered with render_prompt at its path")
    else:
        text = path.read_text(encoding="utf-8")
        if prompt_examples(text) != ids:
            problems.append("the rendered prompt does not hold exactly the submitted examples, in order")
        if reference.student_code.strip() not in text:
            problems.append("the rendered prompt does not hold the student's code")
        if count_tokens(text) != output.total_tokens or output.total_tokens != total:
            problems.append("total_tokens does not match the rendered prompt")
    value = sum(milli(c.similarity) for c in chosen)
    if milli(output.similarity_sum) != value:
        problems.append("similarity_sum is not the chosen examples' sum")
    if problems:
        return result(False, "; ".join(problems), score=0.0, problems=problems)

    best = milli(reference.optimum_similarity_sum)
    score = value / best if best else 1.0
    if value < best:
        return result(
            False,
            f"allowed, but the similarity sum {value / 1000:.3f} is below the best {best / 1000:.3f}",
            score=score,
            best_example_ids=list(reference.optimum_example_ids),
        )
    return result(True, f"the best selection: similarity sum {value / 1000:.3f} in {total} tokens", score=1.0)
