

import yaml
from pydantic import BaseModel, create_model

from progsnap2.database.config import PS2DataWriteConfig
from progsnap2.spec.spec_definition import ProgSnap2Spec


class CORSConfig(BaseModel):
    allow_origins: list[str] = ["*"]
    allow_credentials: bool = True
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]

class PS2APIConfig(BaseModel):
    database_config: PS2DataWriteConfig

    add_server_timestamps: bool = True
    cors_config: CORSConfig = CORSConfig()

    @classmethod
    def from_yaml(cls, yaml_path: str, ps2_spec: ProgSnap2Spec) -> "PS2APIConfig":
        with open(yaml_path, "r", encoding='utf-8') as file:
            data = yaml.safe_load(file)
            config = PS2APIConfig(**data)
            config.database_config.validate_metadata(ps2_spec)
            return config