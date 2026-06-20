from __future__ import annotations

from tutor.evaluation.code_runner import SafeCodeRunner


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    runner = SafeCodeRunner(timeout_seconds=1.0, max_output_chars=1000)

    simple = runner.run("print('hello')")
    _assert(simple["status"] == "success", f"simple print failed: {simple}")
    _assert(simple["stdout"].strip() == "hello", f"unexpected stdout: {simple}")

    exact = runner.run("print(2 + 3)", expected_output="5")
    _assert(exact["passed"] is True, f"expected output match failed: {exact}")

    mismatch = runner.run("print(2 + 3)", expected_output="6")
    _assert(mismatch["execution_status"] == "failed", f"mismatch did not fail: {mismatch}")
    _assert(mismatch["passed"] is False, f"mismatch marked passed: {mismatch}")

    syntax = runner.run("print('oops'")
    _assert(syntax["execution_status"] == "syntax_error", f"syntax error not captured: {syntax}")

    runtime = runner.run("print(1 / 0)")
    _assert(runtime["execution_status"] == "runtime_error", f"runtime error not captured: {runtime}")
    _assert("ZeroDivisionError" in runtime["stderr"], f"runtime stderr missing error: {runtime}")

    import_os = runner.run("import os\nprint(os.getcwd())")
    _assert(import_os["execution_status"] == "blocked", f"import os not blocked: {import_os}")

    open_call = runner.run("open('x.txt', 'w')")
    _assert(open_call["execution_status"] == "blocked", f"open() not blocked: {open_call}")

    eval_call = runner.run("print(eval('2 + 2'))")
    _assert(eval_call["execution_status"] == "blocked", f"eval() not blocked: {eval_call}")

    timeout = runner.run("while True:\n    pass")
    _assert(timeout["execution_status"] == "timeout", f"infinite loop did not time out: {timeout}")

    test_cases = runner.run(
        "print('alpha')\nprint('beta')",
        test_cases=[
            {"name": "contains_alpha", "expected_output": "alpha", "mode": "contains"},
            {"name": "second_line_beta", "expected_output": "beta", "mode": "line_exact", "line_index": 1},
        ],
    )
    _assert(test_cases["passed"] is True, f"test cases did not pass: {test_cases}")
    _assert(len(test_cases["test_results"]) == 2, f"test case results missing: {test_cases}")

    print("simple_print:", simple["execution_status"])
    print("expected_output_match:", exact["execution_status"])
    print("expected_output_mismatch:", mismatch["execution_status"])
    print("syntax_error:", syntax["execution_status"])
    print("runtime_error:", runtime["execution_status"])
    print("import_os:", import_os["execution_status"])
    print("open_call:", open_call["execution_status"])
    print("eval_call:", eval_call["execution_status"])
    print("timeout:", timeout["execution_status"])
    print("test_cases:", test_cases["execution_status"])
    print("STATUS: success")
    print("MODULE: code_runner_test")


if __name__ == "__main__":
    main()
