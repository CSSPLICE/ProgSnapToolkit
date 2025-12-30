import logging
logger = logging.getLogger(__name__)

from abc import ABC, abstractmethod
import pandas as pd

from pandas import DataFrame

from progsnap2.database.codestate.codestate_writer import CodeStateWriter
from progsnap2.database.sql_context import IOContext
from progsnap2.spec.codestate import CodeStateEntry
from progsnap2.spec.metadata import MetadataValues

class PS2Reader(ABC):

    def __init__(self, context: IOContext, codestate_io: CodeStateWriter):
        self.context = context
        self.codestate_io = codestate_io

    @abstractmethod
    def get_main_table(self) -> DataFrame:
        pass

    @abstractmethod
    def get_main_table_head(self, n_rows: int = 5) -> DataFrame:
        pass

    @abstractmethod
    def get_link_table(self, table_name) -> DataFrame:
        pass

    @abstractmethod
    def get_metadata_table(self) -> DataFrame:
        pass

    @abstractmethod
    def get_link_table_names(self) -> list[str]:
        pass

    def get_metadata_values(self) -> MetadataValues:
        """
        Reads the metadata table and returns it as a MetadataValues object.
        """
        metadata_table = None
        try:
            metadata_table = self.get_metadata_table()
        except Exception:
            pass
        if metadata_table is None or metadata_table.empty:
            logger.warning("Warning: Metadata table is empty or not found. Using default values.")
            return MetadataValues()

        if 'Property' not in metadata_table.columns or 'Value' not in metadata_table.columns:
            raise ValueError("Error: DataFrame must contain 'Property' and 'Value' columns.")

        result_dict = metadata_table.set_index('Property')['Value'].to_dict()
        # Replace any NaN values with None to ensure proper handling in MetadataValues
        for key, value in result_dict.items():
            if pd.isna(value):
                result_dict[key] = None
        return MetadataValues(**result_dict)

    def get_codestates_table(self):
        return self.codestate_io.get_codestates_table()

    def get_codestates_table_subset(self, rows: DataFrame) -> DataFrame:
        return self.codestate_io.get_codestates_table_subset(rows)

