"""The explanation prompt: its fixed parts, how an example block is drawn, and the token count.

Tokens are counted with one deterministic rule shared with the verifier: a token is a run of word
characters or a single other non-space character (regex ``\\w+|[^\\w\\s]``). Blocks are joined by
blank lines, so a prompt's tokens are exactly its parts' tokens added up, and an example block's
tokens do not depend on where it sits in the prompt.
"""

from __future__ import annotations

import re

from contract import SkillLevel

TOKEN = re.compile(r"\w+|[^\w\s]")

SYSTEM = {
    SkillLevel.BEGINNER: (
        "You are a patient teaching assistant. The student is a beginner: use plain words, define every "
        "technical term, and walk through one small example input."
    ),
    SkillLevel.INTERMEDIATE: (
        "You are a teaching assistant. The student is intermediate: explain the control flow, name the data "
        "structures used, and give the time complexity informally."
    ),
    SkillLevel.ADVANCED: (
        "You are a teaching assistant. The student is advanced: be concise, give the algorithm, its time and "
        "space complexity in Big-O, and its edge cases."
    ),
}
RULES = (
    "Similar examples from the course bank follow the student's code. Use them only for patterns and "
    "terminology; they are not the student's code."
)
REQUEST = "# Request\nExplain the student's code with the sections What it does, How it works, Key concepts and Watch out for."


def count_tokens(text: str) -> int:
    return len(TOKEN.findall(text))


def example_block(index: int, example_id: str, similarity: float, description: str, code: str) -> str:
    return (
        f"### Example {index}: {example_id} (similarity {similarity:.3f})\n"
        f"Task: {description.strip()}\n```python\n{code.strip()}\n```"
    )


def render(level: SkillLevel, student_code: str, blocks: list[str]) -> str:
    parts = [
        f"# System\n{SYSTEM[level]}\n{RULES}",
        f"# Student's code\n```python\n{student_code.strip()}\n```",
        "# Similar examples (reference only)",
        *blocks,
        REQUEST,
    ]
    return "\n\n".join(parts) + "\n"
