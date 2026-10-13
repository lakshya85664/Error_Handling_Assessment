
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.contracts import ToolCall
from src.gateway import ToolGateway


ROOT = Path(__file__).resolve().parent
EVIDENCE_DIR = ROOT / "evidence"
TRACES_DIR = ROOT / "traces"

EVIDENCE_DIR.mkdir(exist_ok=True)
TRACES_DIR.mkdir(exist_ok=True)


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )


def make_call(request_id, name="order_lookup", arguments=None):
    if arguments is None:
        arguments = {"order_id": "ORD-1001"}

    return ToolCall(
        request_id=request_id,
        name=name,
        version="1.0",
        arguments=arguments,
    )


print("Topic 6 — Evidence Generation")
print("=" * 45)

test_run = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=ROOT,
    capture_output=True,
    text=True,
)

test_output = test_run.stdout + test_run.stderr
(EVIDENCE_DIR / "full_test_output.txt").write_text(
    test_output,
    encoding="utf-8",
)
print(test_output.strip())

gateway = ToolGateway(rate_limit=3, max_retries=2, retry_delay=0)
scenarios = [
    {
        "name": "valid_lookup",
        "call": make_call("evidence-lookup"),
        "role": "support",
        "expected": "ok",
    },
    {
        "name": "invalid_input",
        "call": make_call(
            "evidence-invalid",
            arguments={"order_id": "invalid"},
        ),
        "role": "support",
        "expected": "invalid",
    },
    {
        "name": "unauthorized_update",
        "call": make_call(
            "evidence-denied",
            name="order_update",
            arguments={
                "order_id": "ORD-1001",
                "status": "shipped",
            },
        ),
        "role": "support",
        "expected": "denied",
    },
    {
        "name": "unknown_order",
        "call": make_call(
            "evidence-missing",
            arguments={"order_id": "ORD-9999"},
        ),
        "role": "support",
        "expected": "not_found",
    },
]

scenario_results = []

for scenario in scenarios:
    result = gateway.dispatch(scenario["call"], scenario["role"])
    actual = result.status.value
    passed = actual == scenario["expected"]

    trace = {
        "source": "actual_gateway_execution",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario["name"],
        "request_id": scenario["call"].request_id,
        "tool_name": scenario["call"].name,
        "role": scenario["role"],
        "expected_status": scenario["expected"],
        "actual_status": actual,
        "passed": passed,
        "result": result.model_dump(mode="json"),
    }

    trace_path = TRACES_DIR / f"{scenario['name']}.json"
    write_json(trace_path, trace)

    scenario_results.append(
        {
            "scenario": scenario["name"],
            "expected": scenario["expected"],
            "actual": actual,
            "passed": passed,
            "trace": str(trace_path.relative_to(ROOT)),
        }
    )

    print(
        f"{scenario['name']}: expected={scenario['expected']}, "
        f"actual={actual}, passed={passed}"
    )

report = {
    "project": "Tool Calling Engineering — Topic 6",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "pytest": {
        "command": "python -m pytest -q",
        "exit_code": test_run.returncode,
        "output_file": "evidence/full_test_output.txt",
    },
    "scenarios": scenario_results,
    "scenario_count": len(scenario_results),
    "scenario_pass_count": sum(item["passed"] for item in scenario_results),
    "limitations": [
        "All provider operations use a local fake provider.",
        "Rate limiting and idempotency are in-memory and process-local.",
        "The role is supplied to the gateway and is not authenticated by an identity provider.",
        "Request IDs reused with different payloads are not detected.",
        "The provider failure simulation does not enforce a real network timeout.",
        "Retries are bounded but have no exponential backoff or jitter.",
        "The evidence scenarios do not measure latency or load performance.",
    ],
}

write_json(EVIDENCE_DIR / "operator_report.json", report)

print(
    f"Scenario results: {report['scenario_pass_count']}/"
    f"{report['scenario_count']} passed"
)
print(f"Pytest exit code: {test_run.returncode}")
print("Created: evidence/full_test_output.txt")
print("Created: evidence/operator_report.json")

if test_run.returncode != 0 or report["scenario_pass_count"] != len(scenarios):
    raise SystemExit(1)
