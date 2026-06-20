import ast
import contextlib
import io
import multiprocessing as mp
import traceback
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


DEFAULT_TIMEOUT_SECONDS = 3
MAX_CODE_CHARS = 5000
MAX_OUTPUT_CHARS = 3000


BLOCKED_IMPORTS = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "pathlib",
    "shutil",
    "requests",
    "urllib",
    "http",
    "ftplib",
    "pickle",
    "ctypes",
    "multiprocessing",
    "threading",
    "signal",
    "builtins",
    "importlib",
}

BLOCKED_CALLS = {
    "open",
    "exec",
    "eval",
    "compile",
    "input",
    "__import__",
    "globals",
    "locals",
    "vars",
    "dir",
    "getattr",
    "setattr",
    "delattr",
    "help",
    "exit",
    "quit",
    "breakpoint",
}

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "bool": bool,
    "chr": chr,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "float": float,
    "format": format,
    "hex": hex,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


@dataclass
class CodeRunResult:
    success: bool
    timed_out: bool
    stdout: str
    stderr: str
    error_type: Optional[str]
    error_message: Optional[str]
    blocked: bool
    blocked_reason: Optional[str]


@dataclass
class TestCaseResult:
    test_id: str
    passed: bool
    expected_output: str
    actual_output: str
    stderr: str
    error_message: Optional[str]


def normalize_output(text: Any) -> str:
    if text is None:
        return ""

    text = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(lines).strip()


def trim_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    if text is None:
        return ""

    text = str(text)

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n...[output truncated]"


class SafetyVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors: List[str] = []

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            module_name = alias.name.split(".")[0]
            if module_name in BLOCKED_IMPORTS:
                self.errors.append(f"Blocked import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        module_name = (node.module or "").split(".")[0]
        if module_name in BLOCKED_IMPORTS:
            self.errors.append(f"Blocked import: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        call_name = self._get_call_name(node.func)

        if call_name in BLOCKED_CALLS:
            self.errors.append(f"Blocked function call: {call_name}")

        # Block object/method patterns like os.system if somehow imported.
        if "." in call_name:
            root = call_name.split(".", 1)[0]
            if root in BLOCKED_IMPORTS:
                self.errors.append(f"Blocked unsafe call: {call_name}")

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        # Block dunder access like obj.__dict__, __class__, etc.
        if node.attr.startswith("__"):
            self.errors.append(f"Blocked dunder attribute access: {node.attr}")
        self.generic_visit(node)

    def _get_call_name(self, func: ast.AST) -> str:
        if isinstance(func, ast.Name):
            return func.id

        if isinstance(func, ast.Attribute):
            base = self._get_call_name(func.value)
            return f"{base}.{func.attr}" if base else func.attr

        return ""


def check_code_safety(code: str) -> Dict[str, Any]:
    if not isinstance(code, str):
        return {
            "safe": False,
            "reason": "Code must be a string.",
        }

    if len(code) > MAX_CODE_CHARS:
        return {
            "safe": False,
            "reason": f"Code is too long. Max allowed characters: {MAX_CODE_CHARS}.",
        }

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {
            "safe": True,
            "syntax_error": True,
            "reason": f"SyntaxError: {exc}",
        }

    visitor = SafetyVisitor()
    visitor.visit(tree)

    if visitor.errors:
        return {
            "safe": False,
            "reason": "; ".join(visitor.errors),
        }

    return {
        "safe": True,
        "reason": None,
    }


def _execute_code_worker(code: str, queue: mp.Queue) -> None:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    safe_globals = {
        "__builtins__": SAFE_BUILTINS,
    }

    safe_locals: Dict[str, Any] = {}

    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            exec(code, safe_globals, safe_locals)

        queue.put(
            {
                "success": True,
                "stdout": trim_output(stdout_buffer.getvalue()),
                "stderr": trim_output(stderr_buffer.getvalue()),
                "error_type": None,
                "error_message": None,
            }
        )

    except Exception as exc:
        queue.put(
            {
                "success": False,
                "stdout": trim_output(stdout_buffer.getvalue()),
                "stderr": trim_output(stderr_buffer.getvalue()),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(limit=2),
            }
        )


def run_python_code(code: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
    safety = check_code_safety(code)

    if not safety.get("safe"):
        return asdict(
            CodeRunResult(
                success=False,
                timed_out=False,
                stdout="",
                stderr="",
                error_type="SafetyError",
                error_message=safety.get("reason"),
                blocked=True,
                blocked_reason=safety.get("reason"),
            )
        )

    # Let syntax error be returned as normal execution failure, but without blocking.
    if safety.get("syntax_error"):
        return asdict(
            CodeRunResult(
                success=False,
                timed_out=False,
                stdout="",
                stderr="",
                error_type="SyntaxError",
                error_message=safety.get("reason"),
                blocked=False,
                blocked_reason=None,
            )
        )

    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_execute_code_worker, args=(code, queue))
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join()

        return asdict(
            CodeRunResult(
                success=False,
                timed_out=True,
                stdout="",
                stderr="",
                error_type="TimeoutError",
                error_message=f"Code execution exceeded {timeout_seconds} seconds.",
                blocked=False,
                blocked_reason=None,
            )
        )

    if queue.empty():
        return asdict(
            CodeRunResult(
                success=False,
                timed_out=False,
                stdout="",
                stderr="",
                error_type="ExecutionError",
                error_message="Execution finished without returning a result.",
                blocked=False,
                blocked_reason=None,
            )
        )

    raw_result = queue.get()

    return asdict(
        CodeRunResult(
            success=bool(raw_result.get("success")),
            timed_out=False,
            stdout=raw_result.get("stdout", ""),
            stderr=raw_result.get("stderr", ""),
            error_type=raw_result.get("error_type"),
            error_message=raw_result.get("error_message"),
            blocked=False,
            blocked_reason=None,
        )
    )


def run_python_test_cases(
    code: str,
    test_cases: List[Dict[str, Any]],
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []

    for idx, test_case in enumerate(test_cases, start=1):
        test_id = str(test_case.get("test_id") or f"T{idx}")
        expected_output = str(test_case.get("expected_output", ""))

        # Current simple mode:
        # user code itself should print output.
        # Later we can support function-call tests.
        result = run_python_code(code, timeout_seconds=timeout_seconds)

        actual_output = normalize_output(result.get("stdout", ""))
        expected_norm = normalize_output(expected_output)

        passed = (
            result.get("success") is True
            and actual_output == expected_norm
        )

        results.append(
            asdict(
                TestCaseResult(
                    test_id=test_id,
                    passed=passed,
                    expected_output=expected_output,
                    actual_output=result.get("stdout", ""),
                    stderr=result.get("stderr", ""),
                    error_message=result.get("error_message"),
                )
            )
        )

    passed_count = sum(1 for item in results if item["passed"])
    total = len(results)

    return {
        "success": passed_count == total and total > 0,
        "passed_count": passed_count,
        "total": total,
        "score": round(passed_count / total, 3) if total else 0.0,
        "test_results": results,
    }


def run_self_test() -> None:
    print("\nSafeCodeRunner self-test")
    print("=" * 80)

    examples = [
        {
            "name": "simple_print",
            "code": "x = 5\nprint(x)",
        },
        {
            "name": "syntax_error",
            "code": "for i in range(3)\n    print(i)",
        },
        {
            "name": "blocked_import",
            "code": "import os\nprint(os.listdir('.'))",
        },
        {
            "name": "blocked_open",
            "code": "f = open('secret.txt', 'w')\nprint('done')",
        },
        {
            "name": "timeout",
            "code": "while True:\n    pass",
        },
    ]

    for item in examples:
        print(f"\n{item['name']}")
        print("-" * 80)
        result = run_python_code(item["code"], timeout_seconds=1)
        print(result)

    print("\nTest case check")
    print("-" * 80)
    test_result = run_python_test_cases(
        code="x = 10\nx = 20\nprint(x)",
        test_cases=[
            {
                "test_id": "T1",
                "expected_output": "20",
            }
        ],
    )
    print(test_result)

    print("\nSelf-test complete.")


if __name__ == "__main__":
    run_self_test()