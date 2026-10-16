"""Checks shared by the tool verifiers. Pure functions of their arguments and the files on disk."""

import re

QUERY_ID = re.compile(r"^q\d{2}$")
TOKEN = re.compile(r"\w+|[^\w\s]")  # the same rule as plugin/prompting.py
EXAMPLE = re.compile(r"^### Example (\d+): (\S+) \(similarity", re.MULTILINE)


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def query_id_problem(query_id):
    return None if QUERY_ID.fullmatch(query_id) else f"{query_id!r} is not a query id like q01"


def count_tokens(text):
    return len(TOKEN.findall(text))


def milli(similarity):
    return round(similarity * 1000)


def prompt_path(query_id, level):
    return f"prompts/{query_id}-{level.value}.md"


def prompt_examples(text):
    """The example ids a rendered prompt holds, in order, or None when they are not numbered 1..n."""
    found = EXAMPLE.findall(text)
    if [int(index) for index, _ in found] != list(range(1, len(found) + 1)):
        return None
    return [example_id for _, example_id in found]
