from pydantic import BaseModel

class ReturnItemCreate(BaseModel):
    product_id: int
    quantity: int
    
class ReturnCreate(BaseModel):
    sale_id: int
    reason: str
    items: list[ReturnItemCreate]
    
class ReturnItemResponse(BaseModel):
    product_id: int
    barcode: str
    name: str
    formula: str
    quantity: int
    price: str
    subtotal: str

class ReturnResponse(BaseModel):
    return_id: int
    sale_id: int
    total: str
    reason: str | None
    created_at: str
    items: list[ReturnItemResponse]