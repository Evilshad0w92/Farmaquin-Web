from pydantic import BaseModel

class TicketItem(BaseModel):
    quantity: int
    description: str
    price: str
    discount: str
    total: str

class TicketResponse(BaseModel):
    logo_url: str
    location_name: str
    location_address: str
    employee: str
    payment_method: str
    created_at: str
    items: list[TicketItem]
    total_base: str
    total_discount: str
    total: str
    cash_received: str | None = None
    change_given: str | None = None

class TicketItemReturn(BaseModel):
    quantity: int
    description: str
    price: str
    total: str

class TicketReturnResponse(BaseModel):
    logo_url: str
    location_name: str
    location_address: str
    employee: str
    created_at: str
    items: list[TicketItemReturn]
    total_base: str
    total: str