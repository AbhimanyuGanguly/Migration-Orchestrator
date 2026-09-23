from pydantic import BaseModel, ConfigDict, field_validator

class User(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("name")
    @classmethod
    def name_must_contain_space(cls, v):
        if " " not in v:
            raise ValueError("must contain a space")
        return v
