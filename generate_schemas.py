
import json
from pathlib import Path

from src.schemas import OrderLookupInput, OrderUpdateInput


OUTPUT_DIR = Path("schemas")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

schemas = {
    "order_lookup_input.json": OrderLookupInput,
    "order_update_input.json": OrderUpdateInput,
}

for filename, model in schemas.items():
    output_path = OUTPUT_DIR / filename
    output_path.write_text(
        json.dumps(model.model_json_schema(), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created: {output_path}")
