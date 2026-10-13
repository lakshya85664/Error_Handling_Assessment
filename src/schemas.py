
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderLookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    order_id: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^ORD-[0-9]{4}$",
        description="Order identifier, for example ORD-1001",
    )


class OrderUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    order_id: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^ORD-[0-9]{4}$",
    )
    status: Literal["processing", "shipped", "cancelled"]
