from pydantic import BaseModel
from typing import Literal

class InventoryAdjustmentCreate(BaseModel):
    product_id: int
    adjustment_type: Literal["ENTRADA", "SALIDA"]
    quantity: int
    reason: str

class InventoryAdjustmentResponse(BaseModel):
    id: int
    product_id: int
    adjustment_type: str
    quantity: int
    reason: str
    new_stock: int
    created_at: str