from pydantic import BaseModel, field_validator
from uuid import UUID

class UserCreate(BaseModel):
    username: str
    role: int
    name: str
    password: str
    @field_validator('password')
    @classmethod
    def password_length(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v