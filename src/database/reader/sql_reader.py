from pandas import DataFrame
from database.codestate.codestate_writer import CodeStateWriter
from database.reader.ps2_reader import PS2Reader
from database.sql_context import SQLContext

import pandas as pd
from pandas import DataFrame

from database.sql_table_manager import SQLTableManager
from spec.codestate import CodeStateEntry
from spec.enums import CoreTables


class SQLReader(PS2Reader):

    def __init__(self, context: SQLContext, codestate_io: CodeStateWriter):
        super().__init__(context, codestate_io)

    @property
    def table_manager(self) -> SQLTableManager:
        return self.context.table_manager

    def _get_table(self, table_name: str) -> DataFrame:
        return pd.read_sql_table(
            table_name,
            self.context.conn,
        )

    def add_codestate(self, codestate_id: str, subject_id: str, project_id: str) -> CodeStateEntry:
        # TODO: Now sure how I want to do this yet.
        pass

    def get_main_table(self) -> DataFrame:
        return self._get_table(CoreTables.MainTable)

    def get_metadata_table(self):
        return self._get_table(CoreTables.Metadata)

    def get_link_table(self, table_name):
        if table_name not in self.table_manager.link_tables:
            raise ValueError(f"Table {table_name} does not exist in the database.")

        return self._get_table(table_name)

    def get_link_table_names(self):
        return self.table_manager.link_tables.keys()