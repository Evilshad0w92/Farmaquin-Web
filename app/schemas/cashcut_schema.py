from pydantic import BaseModel

class CashcutClose(BaseModel):
    cash_counted: float
    comment: str | None = None