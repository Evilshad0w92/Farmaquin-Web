from pydantic import BaseModel, field_validator
from uuid import UUID

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int
    
    @field_validator("quantity")
    def validate_quantity(cls, value):
        if value < 1:
            raise ValueError("Producto sin Stock")
        return value

class SaleItemResponse(BaseModel):
    product_id: int
    barcode: str
    name: str
    formula: str
    quantity: int
    stock_before: int
    unit_price: str
    discount_amount: str 
    price_after_discount: str
    line_total: str    

class SaleCreate(BaseModel):
    items: list[SaleItemCreate]
    payment_method: str = "Efectivo"
    cash_received: float | None = None

    @field_validator("items")
    def validate_items(cls, items):
        if len(items) == 0:
            raise ValueError("La venta debe contener al menos un producto")
        return items

class SaleResponse(BaseModel):
    sale_id: int
    total: str
    payment_method: str
    cash_received: str | None = None
    change_given: str | None = None
    created_at: str
    items: list[SaleItemResponse]

