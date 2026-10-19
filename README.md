# Prompt Context Packer

A `nanoagent.plugin/v1` plugin, built with the structure of NanoAgent's
reference plugin, [arxiv-source](https://github.com/zeyuyang8/arxiv-source).
This is the prompt-engineering step of a retrieval-augmented code-explanation
agent. Given a student's code and the examples a MinHash-LSH retriever found
for it, the agent chooses which examples go into the explanation prompt. The
goal is the largest total similarity that fits the token budget. The agent
then renders the prompt. The verifier checks the written prompt and compares
the choice with the best possible one.

## Tools

| Tool | Does | Code |
|---|---|---|
| `list_candidates` | Returns the student's code, the budget and base size of the prompt at a skill level, and each candidate's similarity and token cost | `src/plugin/packer.py` |
| `render_prompt` | Writes the prompt with the given examples, in the given order, to `prompts/<query_id>-<skill_level>.md`, and reports its tokens | `src/plugin/packer.py`, `src/plugin/prompting.py` |
| `best_selection` | Finds the allowed selection with the largest similarity sum by exhaustive search; the `pack-context` reference | `src/plugin/packer.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `pack-context` | Chooses which retrieved examples go into an explanation prompt, for the most similarity within a token budget | `agent`, with `list_candidates` and `render_prompt`; reference `best_selection` |

### The rules

A selection is **allowed** when:

- its examples are distinct candidates;
- each has similarity ≥ `min_similarity` (0.15);
- `base_tokens` + their tokens ≤ `budget_tokens`.

The examples go in the prompt most similar first, with ties broken by
`example_id`.

Tokens follow one deterministic rule, shared by the plugin and the verifier: a
token is a run of word characters or a single other non-space character
(`\w+|[^\w\s]`). Blocks are joined by blank lines, so a prompt's tokens are
exactly the sum of its parts. The budget is the prompt's base size at the
chosen skill level plus each case's example budget.

Before the agent starts, NanoAgent runs `best_selection` and pins every
candidate's similarity and tokens together with the best similarity sum.
`verifier/pack.py` then:

1. **Checks the rules.** It refuses (score 0) a selection with unknown or
   repeated examples, an example below the floor, a total over the budget, or
   the wrong order.
2. **Re-reads the prompt file** that `render_prompt` wrote. The file must hold
   exactly the submitted examples, in order, plus the student's code, and its
   token count must equal `total_tokens`. Submitting a selection other than the
   one rendered fails.
3. **Scores optimality.** An allowed selection scores its similarity sum ÷ the
   best sum, compared in thousandths since similarities have 3 decimals. It is
   valid only when it reaches the best. Any selection that does is accepted,
   not just the reference's.

### The data

`src/plugin/data/queries.json` holds ten cases, `q01` to `q10`. Each is a
student's code (an MBPP test problem) with the 8 MBPP non-test examples whose
AST 4-shingles are most similar to it by exact Jaccard similarity. Some of
them fall below the similarity floor. Each case's budget was chosen so that
adding the most similar examples first is **not** optimal, and a test checks
this for every case.

Data: MBPP, Austin et al. (2021), CC BY 4.0.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output; SkillLevel is an Enum
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs (none)
├── src/plugin/      # the MCP server (__main__.py, IMPLEMENTATIONS), packer.py, prompting.py, data/
├── tests/           # test_verifier.py (correct, wrong, missing, malformed, boundary) and test_packer.py
├── ui/              # outputs drawn from their JSON Schema: renderers.js and renderers.css
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package: tools.py, pack.py, checks.py
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
```

On RUSH Lab, ask the plugin's chat, for example "pack the context for q02 for
a beginner".
