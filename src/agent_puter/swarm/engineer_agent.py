"""
engineer_agent.py — Software Engineer Agent

Writes code, runs tests, and produces file artifacts.
Pattern: LiteLLMModel → pydantic_ai.Agent → .to_a2a() ASGI app.
Each agent owns its own A2A app so it can be mounted or run independently.
"""
import json
import subprocess
import textwrap
from dotenv import load_dotenv
from pydantic_ai import Agent
from .base_agent import make_model

load_dotenv()

_SYSTEM_PROMPT = """
You are the Software Engineer Agent for an autonomous AI consulting agency.

Your responsibilities:
1. Receive implementation tasks from the Project Manager.
2. Write clean, well-documented, production-quality code.
3. Run tests and fix issues before marking a task complete.
4. Return your output as a structured report including:
   - The code produced (in full, not truncated)
   - Test results
   - Any known limitations

Always follow best practices:
  - Use type hints for all functions
  - Write docstrings for every function and class
  - Handle errors gracefully
  - Keep functions small and focused

If you receive QA feedback, address every point systematically before resubmitting.
"""

engineer_agent = Agent(
    model=make_model(),
    instructions=_SYSTEM_PROMPT,
)

# Each agent exposes itself as a self-contained A2A ASGI app.
from .ceo_agent import BASE_URL
engineer_app = engineer_agent.to_a2a(
    name="Engineer Agent",
    url=f"{BASE_URL}/engineer",
    description="Writes, reads, and executes code and automated tests.",
)


@engineer_agent.tool_plain
def write_code(filename: str, language: str, description: str) -> str:
    """
    Record a code generation intent for a given file.

    Args:
        filename: Target filename (e.g. "output/fibonacci.py").
        language: Programming language (e.g. "python", "javascript").
        description: Detailed description of what the code should do.

    Returns a JSON object confirming the code generation request.
    """
    return json.dumps({
        "filename": filename,
        "language": language,
        "description": description,
        "status": "code_generation_requested",
        "note": "LLM will produce the code in its response.",
    })


@engineer_agent.tool_plain
def run_tests(test_command: str, working_directory: str = ".") -> str:
    """
    Execute a test command in a given working directory.

    Args:
        test_command: The shell command to run (e.g. "python -m pytest tests/").
        working_directory: Directory to run the command in (default ".").

    Returns a JSON object with stdout, stderr, and exit code.

    WARNING: Only run trusted commands in sandboxed environments.
    """
    try:
        result = subprocess.run(
            test_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=working_directory,
            timeout=60,
        )
        return json.dumps({
            "command": test_command,
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:1000],
            "passed": result.returncode == 0,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out after 60s", "passed": False})
    except Exception as e:
        return json.dumps({"error": str(e), "passed": False})


@engineer_agent.tool_plain
def read_file(filepath: str) -> str:
    """
    Read a file from disk and return its contents.

    Args:
        filepath: Path to the file to read.

    Returns JSON with the file content or an error message.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        return json.dumps({"filepath": filepath, "content": content[:10_000]})
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {filepath}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@engineer_agent.tool_plain
def write_file(filepath: str, content: str) -> str:
    """
    Write content to a file, creating parent directories as needed.

    Args:
        filepath: Path to the file to write.
        content: Content to write to the file.

    Returns confirmation JSON.
    """
    import os
    try:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))
        return json.dumps({"filepath": filepath, "bytes_written": len(content), "status": "ok"})
    except Exception as e:
        return json.dumps({"error": str(e)})
