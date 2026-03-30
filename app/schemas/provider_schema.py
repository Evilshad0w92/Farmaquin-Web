from pydantic import BaseModel
from typing import Optional

class ProviderCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ProviderUpdate(BaseModel):
    name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ProviderResponse(BaseModel):
    id: int
    name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None