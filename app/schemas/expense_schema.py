from pydantic import BaseModel, field_validator
from decimal import Decimal

class ExpenseCreate(BaseModel):
    amount: Decimal
    description: str
    expense_type: str

    @field_validator("amount")
    def validate_amount(cls, value):
        if value <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        return value


class ExpenseResponse(BaseModel):
    id: int
    amount: str
    description: str
    created_at: str
    expense_type: str


class ExpenseUpdate(BaseModel):
    id: int
    amount: Decimal
    description: str
    expense_type: str

    @field_validator("amount")
    def validate_amount(cls, value):
        if value <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        return value