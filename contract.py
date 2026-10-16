"""Each tool's and task's typed input and output (see nanoagent.plugin.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    LIST_CANDIDATES = "list_candidates"
    RENDER_PROMPT = "render_prompt"
    BEST_SELECTION = "best_selection"


class Task(Enum):
    PACK_CONTEXT = "pack-context"


class SkillLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


QUERY_ID = "A query id, e.g. q01 (the student's code is an MBPP test problem)"
SIMILARITY = "Jaccard similarity of AST 4-shingles with the student's code, 3 decimals"
TOKENS = "Tokens this example's block adds to the prompt"
BUDGET = "The most tokens the whole prompt may have"
BASE = "Tokens of the prompt with no examples (system prompt, student's code, request) at this skill level"
MIN_SIMILARITY = "Examples below this similarity may not be used"


@dataclass
class PackInput(Output):
    query_id: Annotated[str, QUERY_ID]
    skill_level: Annotated[SkillLevel, "The student's level; it sets the system prompt"]


@dataclass
class Candidate(Output):
    example_id: Annotated[str, "The example's id, e.g. mbpp-602"]
    description: Annotated[str, "The task the example solves"]
    similarity: Annotated[float, SIMILARITY]
    tokens: Annotated[int, TOKENS]


@dataclass
class CandidatesOutput(Output):
    query_id: Annotated[str, QUERY_ID]
    skill_level: Annotated[SkillLevel, "The student's level"]
    student_code: Annotated[str, "The code the prompt asks the model to explain"]
    budget_tokens: Annotated[int, BUDGET]
    base_tokens: Annotated[int, BASE]
    min_similarity: Annotated[float, MIN_SIMILARITY]
    candidates: Annotated[list[Candidate], "The retrieved examples, most similar first"]


@dataclass
class RenderInput(Output):
    query_id: Annotated[str, QUERY_ID]
    skill_level: Annotated[SkillLevel, "The student's level"]
    example_ids: Annotated[list[str], "The examples to include, in the order they should appear"]


@dataclass
class RenderOutput(Output):
    query_id: Annotated[str, QUERY_ID]
    skill_level: Annotated[SkillLevel, "The student's level"]
    path: Annotated[str, "The prompt file, prompts/<query_id>-<skill_level>.md in the workspace"]
    example_ids: Annotated[list[str], "The examples included, in prompt order"]
    total_tokens: Annotated[int, "Tokens of the whole rendered prompt"]
    budget_tokens: Annotated[int, BUDGET]
    within_budget: Annotated[bool, "Whether total_tokens is at most budget_tokens"]
    similarity_sum: Annotated[float, "The included examples' similarities summed, 3 decimals"]


@dataclass
class ScoredCandidate(Output):
    example_id: Annotated[str, "The example's id"]
    similarity: Annotated[float, SIMILARITY]
    tokens: Annotated[int, TOKENS]


@dataclass
class BestOutput(Output):
    query_id: Annotated[str, QUERY_ID]
    skill_level: Annotated[SkillLevel, "The student's level"]
    student_code: Annotated[str, "The code the prompt asks the model to explain"]
    budget_tokens: Annotated[int, BUDGET]
    base_tokens: Annotated[int, BASE]
    min_similarity: Annotated[float, MIN_SIMILARITY]
    candidates: Annotated[list[ScoredCandidate], "Every candidate with its similarity and tokens"]
    optimum_similarity_sum: Annotated[float, "The largest similarity sum any allowed selection reaches"]
    optimum_example_ids: Annotated[list[str], "One selection that reaches it, in prompt order"]


@dataclass
class PackOutput(Output):
    query_id: Annotated[str, QUERY_ID]
    skill_level: Annotated[SkillLevel, "The student's level"]
    example_ids: Annotated[list[str], "The chosen examples in prompt order: most similar first, ties by example_id"]
    path: Annotated[str, "The rendered prompt file, exactly as render_prompt returned it"]
    total_tokens: Annotated[int, "Tokens of the rendered prompt, as render_prompt returned it"]
    similarity_sum: Annotated[float, "The chosen examples' similarities summed, 3 decimals"]


TOOLS = {
    Tool.LIST_CANDIDATES: (PackInput, CandidatesOutput),
    Tool.RENDER_PROMPT: (RenderInput, RenderOutput),
    Tool.BEST_SELECTION: (PackInput, BestOutput),
}
TASKS = {Task.PACK_CONTEXT: (PackInput, PackOutput)}
