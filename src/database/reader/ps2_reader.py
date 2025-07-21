from abc import ABC, abstractmethod

from pandas import DataFrame

from database.codestate.codestate_writer import CodeStateWriter
from database.sql_context import IOContext
from spec.codestate import CodeStateEntry

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