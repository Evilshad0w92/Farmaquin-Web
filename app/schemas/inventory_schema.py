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

class InventoryNewItemCreate(BaseModel):
    barcode: str
    name: str
    formula: str
    lab_name: str
    method: str
    unit_cost: float
    sell_price: float
    stock: int
    min_stock: int
    section_id: int
    provider_id: int

class InventoryNewItemResponse(BaseModel):
    id: int
    barcode: str
    name: str
    formula: str
    lab_name: str
    method: str
    unit_cost: str
    sell_price: str
    stock: int
    min_stock: int
    section_id: int
    section_name: str
    provider_id: int
    provider_name: str
    location_id: int
    location_name: str
    created_at: str
    
class InventoryEditCreate(BaseModel):
    product_id: int
    name: str
    formula: str
    lab_name: str
    method: str
    unit_cost: float
    sell_price: float
    min_stock: int
    section_id: int
    provider_id: int

class InventoryEditResponse(BaseModel):
    id: int
    product_id: int
    name: str
    formula: str
    lab_name: str
    method: str
    unit_cost: float
    sell_price: float
    min_stock: int
    section_id: int
    provider_id: int
    created_at: str

class labListResponse(BaseModel):
    lab_name: str