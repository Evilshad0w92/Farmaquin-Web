from pydantic import BaseModel, field_validator

class ExpenseCreate(BaseModel):
    expense_type: str
    amount: float
    description: str

    @field_validator("amount")
    def validate_amount(cls, value):
        if value <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        return value
    
class ExpenseResponse(BaseModel):
    id: int
    expense_type: str
    amount: str
    description: str
    created_at: str
