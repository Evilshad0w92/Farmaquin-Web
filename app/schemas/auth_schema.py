from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str
    box_id: int

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
