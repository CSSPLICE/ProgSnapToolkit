from pandas import DataFrame
from progsnap2.database.codestate.codestate_writer import CodeStateWriter
from progsnap2.database.reader.ps2_reader import PS2Reader
from progsnap2.database.sql_context import SQLContext

import pandas as pd
from pandas import DataFrame

from progsnap2.database.sql_table_manager import SQLWriterTableManager
from progsnap2.spec.codestate import CodeStateEntry
from progsnap2.spec.enums import CoreTables, MainTableColumns as Cols

from sqlalchemy import text
from sqlalchemy import select


class SQLReader(PS2Reader):

    def __init__(self, context: SQLContext, codestate_io: CodeStateWriter):
        super().__init__(context, codestate_io)
        self.table_names = context.table_manager.table_names

    def _get_table(self, table_name: str) -> DataFrame:
        return pd.read_sql_table(
            table_name,
            self.context.conn,
        )

    def get_main_table(self) -> DataFrame:
        return self._get_table(CoreTables.MainTable)

    def get_main_table_head(self, n_rows = 5):
        main_table = self.context.table_manager.get_table(CoreTables.MainTable)
        statement = select(main_table).limit(n_rows)
        return pd.read_sql(statement, self.context.conn)

    def get_metadata_table(self):
        return self._get_table(self.context.data_config.metadata_table_name)

    def get_link_table(self, table_name):
        if table_name not in self.table_names:
            with_link = "Link" + table_name
            if with_link in self.table_names:
                table_name = with_link
            else:
                raise ValueError(f"Table {table_name} does not exist in the database.")

        return self._get_table(table_name)

    def get_link_table_names(self):
        core_tables = [CoreTables.MainTable, CoreTables.Metadata, CoreTables.CodeStates]
        return [name for name in self.table_names if name not in core_tables]
