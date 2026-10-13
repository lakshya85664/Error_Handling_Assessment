# Topic 6 — Implement Error Handling in Code

**Course:** Tool Calling Engineering  
**Assessment:** Error Handling Assessment  
**Implementation:** Python, Pydantic, pytest  
**Verified results:** 50 automated tests passed; 4/4 evidence scenarios passed

## 1. Project Overview

This project implements a local tool-calling gateway that validates requests, checks tool registration and role permissions, validates tool-specific arguments, invokes a fake order provider, normalizes failures into stable statuses, and emits structured event records. It demonstrates predictable outcomes for successful and failed tool calls without exposing arbitrary exception details.

The provider is intentionally fake and in-memory. No real orders are accessed or changed.

## 2. Architecture

1. **Contracts (`src/contracts.py`)** — defines `ToolCall`, `ToolResult`, public error statuses, and next actions.
2. **Registry (`src/registry.py`)** — registers versioned tools with input models, handlers, allowed roles, and read/write classification.
3. **Schemas (`src/schemas.py`)** — Pydantic schemas validate order identifiers and allowed order statuses.
4. **Fake provider (`src/providers.py`)** — supplies sample orders and controllable timeout/unavailability failures.
5. **Gateway (`src/gateway.py`)** — validates requests, checks registration and authorization, applies rate limiting, validates arguments, retries selected provider errors within a configured bound, normalizes outcomes, caches completed results, and records events.
6. **Reliability (`src/reliability.py`)** — provides a process-local sliding-window rate limiter and idempotency result store.
7. **Observability (`src/observability.py`)** — records JSON-serializable event metadata without logging raw tool arguments.
8. **Evidence** — pytest output, JSON traces, metrics summary, and operator report.

## 3. Error-Handling Behaviors

The gateway returns stable statuses including `ok`, `invalid`, `denied`, `not_found`, `timeout`, `retry_exhausted`, `rate_limited`, and `failed`. Invalid input is rejected before provider execution. Role permissions are checked before handler execution. Provider timeout and unavailability exceptions are retried up to the configured maximum; retries are bounded. Unexpected exception messages are not returned to callers.

The order lookup tool is available to `support` and `admin`. The order update tool is restricted to `admin`. These are application-level checks in this educational implementation, not a substitute for trusted authentication.

## 4. Setup

Use Windows CMD from the project directory.

```cmd
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` pins the tested versions: `pydantic==2.14.1`, `pytest==9.1.1`, and `httpx==0.28.1`.

## 5. Run the Project Checks

```cmd
python -m pytest -q
python generate_schemas.py
python generate_metrics.py
python generate_evidence.py
python -m json.tool evidence\operator_report.json
```

The latest verified run reported **50 passed** and **4/4 evidence scenarios passed**.

## 6. Evidence Artifacts

Expected generated files include:

- `schemas/order_lookup_input.json`
- `schemas/order_update_input.json`
- `traces/valid_lookup.json`
- `traces/invalid_input.json`
- `traces/unauthorized_update.json`
- `traces/unknown_order.json`
- `evidence/full_test_output.txt`
- `evidence/metrics_summary.json`
- `evidence/operator_report.json`
- `architecture.mmd`

The traces are produced by actual executions of the local gateway and fake provider. The report records the expected and actual status for each scenario.

## 7. Security and Reliability Limitations

- **Fake provider:** all order operations are local examples; no external order service is contacted.
- **Identity trust boundary:** the gateway receives a role argument. A production service must derive identity and permissions from trusted authentication and authorization middleware.
- **Process-local state:** rate limiting and idempotency are held in memory and are not shared across worker processes or restarts.
- **Idempotency key reuse:** the current store does not detect the same request ID being reused with a different payload.
- **Timeout model:** provider timeout exceptions are simulated. There is no network client deadline or real upstream timeout.
- **Retry policy:** retries are bounded, but exponential backoff, jitter, and operation-specific retry classification require further production hardening.
- **Evidence scope:** the evidence scenarios are functional checks, not load, latency, or production security testing.

## 8. Reflection (Approximately 300 Words)

Building this assessment helped me understand that reliable tool calling requires more than writing a handler that works on a successful request. A tool gateway must define a stable contract for both success and failure, validate inputs before execution, and make permission decisions before allowing a potentially sensitive operation. Using Pydantic schemas made the input rules explicit and testable, while a registry made each tool's version, permissions, handler, and read/write classification discoverable.

A major learning outcome was the importance of translating implementation failures into predictable public statuses. Callers should be able to distinguish invalid input, denied access, missing resources, timeouts, rate limits, and unexpected failures without receiving internal exception details. The fake provider made it possible to exercise these paths repeatedly without contacting an external service or changing real data.

I also learned that reliability features must be tested at the integration boundary. A rate limiter or idempotency store can pass unit tests but still be incorrectly wired into a gateway. Likewise, a retry test should verify the number of attempts, not only the final status. Structured JSON traces and an operator report provide evidence of what the gateway actually returned for selected scenarios, while pytest gives a repeatable regression check.

The project is an educational implementation rather than a production-ready service. Its in-memory reliability state is process-local, its role argument is not authenticated, and its provider failures are simulated. The current idempotency store also does not reject reuse of a request ID with different arguments. A production version would need trusted identity middleware, shared durable storage, payload-aware idempotency, real upstream deadlines, carefully classified retries with backoff and jitter, and monitoring under load.

Overall, this project strengthened my understanding of defensive API design, error normalization, test-driven development, and the difference between demonstrating a reliability mechanism and proving it is safe to operate in production.
