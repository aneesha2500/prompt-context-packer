"""list_candidates, render_prompt and best_selection: each call's input and output."""

from pathlib import Path

from .checks import count_tokens, milli, prompt_examples, prompt_path, query_id_problem, result


def verify_input(value):
    problem = query_id_problem(value.query_id)
    return result(False, problem) if problem else result(True, "input is valid")


def verify_render_input(value):
    problem = query_id_problem(value.query_id)
    if problem:
        return result(False, problem)
    if len(set(value.example_ids)) != len(value.example_ids):
        return result(False, "example_ids must be distinct")
    return result(True, "input is valid")


def verify_candidates(input_value, output_value, workspace):
    if output_value.query_id != input_value.query_id or output_value.skill_level != input_value.skill_level:
        return result(False, "output is for another query or level")
    ids = [c.example_id for c in output_value.candidates]
    if len(set(ids)) != len(ids) or not ids:
        return result(False, "candidates must be distinct and not empty")
    if [c.similarity for c in output_value.candidates] != sorted((c.similarity for c in output_value.candidates), reverse=True):
        return result(False, "candidates must be most similar first")
    if output_value.base_tokens >= output_value.budget_tokens or any(c.tokens <= 0 for c in output_value.candidates):
        return result(False, "token counts are inconsistent")
    return result(True, f"{len(ids)} candidates")


def verify_render(input_value, output_value, workspace):
    expected = prompt_path(input_value.query_id, input_value.skill_level)
    if output_value.path != expected or list(output_value.example_ids) != list(input_value.example_ids):
        return result(False, "the prompt is not the requested one")
    path = Path(workspace) / output_value.path
    if not path.is_file():
        return result(False, f"{expected} was not written")
    text = path.read_text(encoding="utf-8")
    if count_tokens(text) != output_value.total_tokens:
        return result(False, "total_tokens is not the token count of the written prompt")
    if prompt_examples(text) != list(input_value.example_ids):
        return result(False, "the written prompt does not hold exactly the requested examples, in order")
    if output_value.within_budget != (output_value.total_tokens <= output_value.budget_tokens):
        return result(False, "within_budget does not match the token counts")
    return result(True, f"{expected} written, {output_value.total_tokens} tokens")


def verify_best(input_value, output_value, workspace):
    if output_value.query_id != input_value.query_id:
        return result(False, "output is for another query")
    by_id = {c.example_id: c for c in output_value.candidates}
    chosen = [by_id.get(i) for i in output_value.optimum_example_ids]
    if None in chosen:
        return result(False, "the optimum names an unknown example")
    tokens = output_value.base_tokens + sum(c.tokens for c in chosen)
    if tokens > output_value.budget_tokens or any(c.similarity < output_value.min_similarity for c in chosen):
        return result(False, "the optimum breaks the budget or the similarity floor")
    if sum(milli(c.similarity) for c in chosen) != milli(output_value.optimum_similarity_sum):
        return result(False, "optimum_similarity_sum is not the chosen examples' sum")
    return result(True, "the reference selection is allowed")
