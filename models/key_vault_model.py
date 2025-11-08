from pydantic import BaseModel


class SecretResponse(BaseModel):
    status: str
    secret_name: str
    has_value: bool
    message: str
