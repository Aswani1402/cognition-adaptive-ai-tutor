from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


FORBIDDEN_IMPORT_ROOTS = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "pathlib",
    "shutil",
    "glob",
    "importlib",
    "urllib",
    "http",
    "ftplib",
    "requests",
}

FORBIDDEN_CALLS = {
    "open",
    "eval",
    "exec",
    "__import__",
    "compile",
    "input",
}

FORBIDDEN_NAMES = {
    "__builtins__",
    "__loader__",
    "__spec__",
    "__package__",
    "__file__",
}

DEFAULT_ALLOWED_BUILTINS = [
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
    "len",
    "list",
    "max",
    "min",
    "pow",
    "print",
    "range",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
]


def _base_result(
    execution_status: str,
    status: str = "error",
    stdout: str = "",
    stderr: str = "",
    error: str | None = None,
    passed: bool = False,
    score: float = 0.0,
    expected_output: str | None = None,
    actual_output: str | None = None,
    test_results: list[dict[str, Any]] | None = None,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "execution_status": execution_status,
        "stdout": stdout,
        "stderr": stderr,
        "error": error,
        "passed": passed,
        "score": max(0.0, min(1.0, float(score))),
        "expected_output": expected_output,
        "actual_output": actual_output if actual_output is not None else stdout,
        "test_results": test_results or [],
        "blocked_reason": blocked_reason,
    }


def _truncate(value: str, max_output_chars: int) -> str:
    if len(value) <= max_output_chars:
        return value
    return value[:max_output_chars] + "\n...[output truncated]"


def _name_from_call(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = [func.attr]
        current = func.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        parts.reverse()
        return ".".join(parts)
    return None


def inspect_code_safety(code: str) -> dict[str, Any]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {
            "safe": False,
            "syntax_error": True,
            "reason": f"{exc.msg} at line {exc.lineno}",
        }

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif node.module:
                names = [node.module]

            for name in names:
                root = name.split(".")[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    return {
                        "safe": False,
                        "syntax_error": False,
                        "reason": f"Import blocked: {root}",
                    }

            return {
                "safe": False,
                "syntax_error": False,
                "reason": "Imports are blocked in SafeCodeRunner.",
            }

        if isinstance(node, ast.Call):
            call_name = _name_from_call(node)
            root_name = call_name.split(".")[0] if call_name else None
            if root_name in FORBIDDEN_CALLS:
                return {
                    "safe": False,
                    "syntax_error": False,
                    "reason": f"Call blocked: {root_name}",
                }

        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return {
                "safe": False,
                "syntax_error": False,
                "reason": f"Name blocked: {node.id}",
            }

    return {"safe": True, "syntax_error": False, "reason": None}


def _sandbox_source(user_code: str) -> str:
    builtins_literal = repr(DEFAULT_ALLOWED_BUILTINS)
    return f"""
import builtins as _builtins

_allowed = {builtins_literal}
_safe_builtins = {{name: getattr(_builtins, name) for name in _allowed}}
_globals = {{"__builtins__": _safe_builtins}}
_code = {user_code!r}
exec(_code, _globals, None)
"""


def _compare_output(actual: str, expected: str | None) -> tuple[bool, float]:
    if expected is None:
        return True, 1.0
    return actual.strip() == str(expected).strip(), 1.0 if actual.strip() == str(expected).strip() else 0.0


def run_python_code(
    code: str,
    expected_output: str | None = None,
    test_cases: list[dict[str, Any]] | None = None,
    timeout_seconds: float = 2.0,
    max_output_chars: int = 4000,
) -> dict[str, Any]:
    safety = inspect_code_safety(code)
    if not safety["safe"]:
        if safety.get("syntax_error"):
            return _base_result(
                execution_status="syntax_error",
                stderr=str(safety["reason"]),
                error=str(safety["reason"]),
                expected_output=expected_output,
            )

        return _base_result(
            execution_status="blocked",
            error=str(safety["reason"]),
            expected_output=expected_output,
            blocked_reason=str(safety["reason"]),
        )

    with tempfile.TemporaryDirectory(prefix="safe_code_runner_") as tmp_dir:
        script_path = Path(tmp_dir) / "runner.py"
        script_path.write_text(_sandbox_source(code), encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, "-I", str(script_path)],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _truncate(exc.stdout or "", max_output_chars)
            stderr = _truncate(exc.stderr or "", max_output_chars)
            return _base_result(
                execution_status="timeout",
                stdout=stdout,
                stderr=stderr,
                error=f"Execution timed out after {timeout_seconds} seconds.",
                expected_output=expected_output,
                actual_output=stdout,
            )

    stdout = _truncate(completed.stdout or "", max_output_chars)
    stderr = _truncate(completed.stderr or "", max_output_chars)

    if completed.returncode != 0:
        return _base_result(
            execution_status="runtime_error",
            stdout=stdout,
            stderr=stderr,
            error=stderr.strip() or f"Process exited with code {completed.returncode}.",
            expected_output=expected_output,
            actual_output=stdout,
        )

    output_matches, output_score = _compare_output(stdout, expected_output)
    test_results = _run_basic_test_cases(stdout, test_cases)
    tests_passed = all(item.get("passed") for item in test_results) if test_results else True

    passed = output_matches and tests_passed
    score_parts = [output_score]
    if test_results:
        score_parts.append(sum(1 for item in test_results if item.get("passed")) / len(test_results))
    score = sum(score_parts) / len(score_parts)

    return _base_result(
        status="success",
        execution_status="passed" if passed else "failed",
        stdout=stdout,
        stderr=stderr,
        error=None if passed else "Output or test case mismatch.",
        passed=passed,
        score=score,
        expected_output=expected_output,
        actual_output=stdout,
        test_results=test_results,
    )


def _run_basic_test_cases(stdout: str, test_cases: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not test_cases:
        return []

    lines = stdout.splitlines()
    results = []
    for index, case in enumerate(test_cases, start=1):
        expected = str(case.get("expected_output", ""))
        mode = str(case.get("mode", "contains"))
        if mode == "exact":
            passed = stdout.strip() == expected.strip()
        elif mode == "line_exact":
            line_index = int(case.get("line_index", index - 1))
            actual_line = lines[line_index] if 0 <= line_index < len(lines) else ""
            passed = actual_line.strip() == expected.strip()
        else:
            passed = expected in stdout

        results.append(
            {
                "name": case.get("name", f"test_case_{index}"),
                "mode": mode,
                "expected_output": expected,
                "passed": passed,
            }
        )
    return results


class SafeCodeRunner:
    def __init__(self, timeout_seconds: float = 2.0, max_output_chars: int = 4000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    def run(
        self,
        code: str,
        expected_output: str | None = None,
        test_cases: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return run_python_code(
            code=code,
            expected_output=expected_output,
            test_cases=test_cases,
            timeout_seconds=self.timeout_seconds,
            max_output_chars=self.max_output_chars,
        )
