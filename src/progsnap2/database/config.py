import logging
logger = logging.getLogger(__name__)

import os
from typing import Optional
from pydantic import BaseModel, create_model, model_validator
import yaml

from progsnap2.spec.spec_definition import Metadata, ProgSnap2Spec

def create_metadata_values_model(metadata_spec: Metadata) -> type[BaseModel]:
    fields = {}
    for property in metadata_spec.properties:
        fields[property.name] = (Optional[property.datatype.python_type], property.default_value)
    return create_model("MetadataValues", **fields)

class PS2DataConfig(BaseModel):
    root_path: str
    """The root directory of the PrgoSnap2 dataset."""

    metadata: object = None
    """Metadata for the dataset. If None, it will be loaded from the metadata file."""

    metadata_table_name: str = "DatasetMetadata"
    """Name of the metadata table (without an extension)."""

    # Config for CSV format
    main_table_file: str = None
    """Relative path to the main table CSV file."""
    codestates_table_relative_path: str = "CodeStates.csv"
    """Relative path to the CodeStates table CSV file."""

    # Config for SQL/SQLite format
    sqlalchemy_url: str = None
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 0
    pool_timeout: float = 2
    pool_recycle: int = 60 * 60 # 1 hour

    @property
    def is_sql_config(self) -> bool:
        return self.sqlalchemy_url is not None

    @property
    def is_csv_config(self) -> bool:
        return self.main_table_file is not None

    @property
    def codestates_table_path(self) -> str:
        return os.path.join(self.root_path, self.codestates_table_relative_path)

    @property
    def metadata_path(self) -> str:
        file = self.metadata_table_name
        if not file.lower().endswith('.csv'):
            file += '.csv'
        return os.path.join(self.root_path, file)

    @property
    def main_table_path(self) -> str:
        if self.is_csv_config:
            return os.path.join(self.root_path, self.main_table_file)
        raise ValueError("Main table path is only available for CSV configurations.")

    @model_validator(mode="after")
    def validate_has_path_or_url(cls, values):
        if not values.main_table_file and not values.sqlalchemy_url:
            raise ValueError("Either main_table_file or sqlalchemy_url must be provided.")
        if values.main_table_file and values.sqlalchemy_url:
            raise ValueError("Only one of main_table_file or sqlalchemy_url can be provided.")
        return values

    @property
    def codestates_dir(self) -> str:
        return os.path.join(self.root_path, "CodeStates")

    def validate_metadata(self, spec: ProgSnap2Spec) -> bool:
        metadata_class = create_metadata_values_model(spec.metadata)
        if self.metadata is None:
            return True
        try:
            self.metadata = metadata_class(**self.metadata)
            return True
        except ValueError as e:
            logger.warning(f"Metadata validation error: {e}")
            return False

    @classmethod
    def from_yaml(cls, yaml_path: str, spec: ProgSnap2Spec) -> "PS2DataWriteConfig":
        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)
        config = cls(**data)
        config.validate_metadata(spec)
        return config


class PS2DataWriteConfig(PS2DataConfig):

    optimize_codestate_ids: bool
    """If true, provided CodeStateIDs are assumed to be local
    to each logging call and will be regenerated to be globally
    unique. If false, the provided CodeStateIDs are used directly.
    """

    codestates_have_sections: bool = True

    short_str_length: int = 255
    # Keep it relatively short, since many databases have limits on index and row lengths
    path_str_length: int = 512

    indexed_columns: list[str] = []
    """List of column names to create indexes for in the main table."""