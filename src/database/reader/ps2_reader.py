from abc import ABC, abstractmethod

from pandas import DataFrame

from database.codestate.codestate_writer import CodeStateWriter
from database.sql_context import IOContext
from spec.codestate import CodeStateEntry
from spec.metadata import MetadataValues

class PS2Reader(ABC):

    def __init__(self, context: IOContext, codestate_io: CodeStateWriter):
        self.context = context
        self.codestate_io = codestate_io

    @abstractmethod
    def get_main_table(self) -> DataFrame:
        pass

    @abstractmethod
    def add_codestate(self, codestate_id: str, subject_id: str, project_id: str) -> CodeStateEntry:
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

    @abstractmethod
    def get_codestates_table(self) -> DataFrame:
        pass

    @abstractmethod
    def get_codestates_table_subset(self, codestate_ids: list[str]) -> DataFrame:
        pass

    def get_metadata_values(self) -> MetadataValues:
        """
        Reads the metadata table and returns it as a MetadataValues object.
        """
        metadata_table = None
        try:
            self.get_metadata_table()
        except Exception:
            pass
        if metadata_table is None or metadata_table.empty:
            print("Warning: Metadata table is empty or not found. Using default values.")
            return MetadataValues()

        if 'Property' not in metadata_table.columns or 'Value' not in metadata_table.columns:
            raise ValueError("Error: DataFrame must contain 'Property' and 'Value' columns.")

        result_dict = metadata_table.set_index('Property')['Value'].to_dict()
        return MetadataValues(**result_dict)