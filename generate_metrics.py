
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent
EVIDENCE_DIR = ROOT / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)

test_files = sorted((ROOT / "tests").glob("test_*.py"))

metrics = {
    "project": "Error Handling Assessment",
    "test_files": len(test_files),
    "test_file_names": [path.name for path in test_files],
    "reliability_features": {
        "bounded_retries": True,
        "process_local_rate_limiting": True,
        "process_local_idempotency": True,
        "structured_event_logging": True,
    },
    "limitations": [
        "The provider is a local fake implementation.",
        "Rate limiting and idempotency are process-local.",
        "The gateway accepts a role argument; production authentication must supply trusted identity.",
        "Request ID reuse with different payloads is not yet detected.",
        "The timeout test does not prove an external network timeout or enforce a wall-clock deadline.",
    ],
}

output = EVIDENCE_DIR / "metrics_summary.json"
output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
print(f"Created: {output}")
print(f"Test files discovered: {len(test_files)}")
