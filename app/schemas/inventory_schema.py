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

class InventoryRestockCreate(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float
    sell_price: float
    provider_id: int

class InventoryRestockResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_cost: str
    sell_price: str
    provider_id: int
    provider_name: str
    new_stock: int
    created_at: str