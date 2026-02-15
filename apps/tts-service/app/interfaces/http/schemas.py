from pydantic import BaseModel, Field


class LmValidateRequest(BaseModel):
    model_id: str = Field(min_length=1)


class LmValidateResponse(BaseModel):
    valid: bool
    reason: str | None = None
