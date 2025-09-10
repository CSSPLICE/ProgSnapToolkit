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

    def get_codestates_table(self):
        return self._get_table(CoreTables.CodeStates)

    def get_codestates_table_subset(self, codestate_ids: list[str]) -> DataFrame:
        """
        Returns a subset of the CodeStates table for the given list of codestate IDs.
        :param codestate_ids: List of codestate IDs to filter by.
        :return: DataFrame containing the filtered CodeStates.
        """
        if not self.context.data_config.sqlalchemy_url.lower().startswith("sqlite://"):
            raise ValueError("This method is only supported for SQLite databases.")

        temp_table_name = "temp_ids"
        self._create_temp_id_table(temp_table_name, codestate_ids)

        # Join the temporary table with CodeStateIDs to fetch with
        # the CodeStates table.
        return pd.read_sql(f"""
            SELECT cs.*
            FROM {CoreTables.CodeStates} cs
            JOIN temp_ids temp ON cs.{Cols.CodeStateID} = temp.{Cols.CodeStateID}
        """, self.context.conn)

    def _create_temp_id_table(self, temp_table_name, codestate_ids: list[str]) -> DataFrame:
        conn = self.context.conn

        # Remove the table if it exists
        conn.execute(text(f"DROP TABLE IF EXISTS {temp_table_name};"))
        # Create a temporary table
        conn.execute(text(f"CREATE TEMP TABLE {temp_table_name} ({Cols.CodeStateID} INTEGER);"))

        # Insert rows
        conn.execute(
            text(f"INSERT INTO {temp_table_name} ({Cols.CodeStateID}) VALUES (:id);"),
            [{"id": int(i)} for i in codestate_ids]
        )

