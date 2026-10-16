"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import pack, tools


class _Candidates:
    verify_input = staticmethod(tools.verify_input)
    verify_output = staticmethod(tools.verify_candidates)


class _Render:
    verify_input = staticmethod(tools.verify_render_input)
    verify_output = staticmethod(tools.verify_render)


class _Best:
    verify_input = staticmethod(tools.verify_input)
    verify_output = staticmethod(tools.verify_best)


TOOLS = {Tool.LIST_CANDIDATES: _Candidates, Tool.RENDER_PROMPT: _Render, Tool.BEST_SELECTION: _Best}
# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.PACK_CONTEXT: pack.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
