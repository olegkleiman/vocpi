from typing import Optional
from pydantic import BaseModel
import json
from pathlib import Path

class TokenPayload(BaseModel):
    uid: str
    type: str
    auth_id: str
    visual_number: Optional[str]
    issuer: str
    valid: bool
    whitelist: str
    last_updated: str
    session_id: str

    @classmethod
    def from_json_file(cls, file_path: str):
        path = Path(file_path)
        if path.exists():
            return cls.model_validate_json(path.read_text())
        raise FileNotFoundError(f"Token file not found: {file_path}")


