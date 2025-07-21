from pandas import DataFrame
from database.codestate.codestate_writer import CodeStateWriter
from database.reader.ps2_reader import PS2Reader
from database.sql_context import SQLContext

import pandas as pd
from pandas import DataFrame

from database.sql_table_manager import SQLTableManager
from spec.codestate import CodeStateEntry
from spec.enums import CoreTables, MainTableColumns as Cols

from sqlalchemy import text
from sqlalchemy.orm import Session


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
        # TODO: THe docs actually say it should be DatasetMetadata
        # so this enum may need to be updated. There's also no way to
        # configure it right now...
        return self._get_table(CoreTables.Metadata)

    def get_link_table(self, table_name):
        if table_name not in self.table_manager.link_tables:
            raise ValueError(f"Table {table_name} does not exist in the database.")

        return self._get_table(table_name)

    def get_link_table_names(self):
        return self.table_manager.link_tables.keys()

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
            SELECT *
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

