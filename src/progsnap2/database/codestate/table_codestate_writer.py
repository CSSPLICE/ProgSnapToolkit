import logging
logger = logging.getLogger(__name__)

import csv
from sqlalchemy import insert, text
from progsnap2.database.codestate.codestate_writer import ContextualCodeStateEntry, CodeStateWriter
from progsnap2.database.config import PS2DataWriteConfig
from progsnap2.database.sql_context import IOContext, SQLContext
from progsnap2.spec.enums import CodeStatesTableColumns as Cols, CoreTables
import os
import pandas as pd
from pandas import DataFrame

class CSVTableCodeStateWriter(CodeStateWriter):

    def __init__(self, data_config: PS2DataWriteConfig):
        super().__init__()
        self.config = data_config
        self.written_codestate_ids = set()

        self.initialize_codestate_ids()

    def initialize_codestate_ids(self):
        file_path = self.config.codestates_table_path
        if not os.path.exists(file_path):
            return

        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                codestate_id = row[Cols.CodeStateID]
                self.written_codestate_ids.add(codestate_id)

    def add_codestate_and_get_id(self, codestate: ContextualCodeStateEntry) -> str:
        codestate_id = self.get_codestate_id_from_hash(codestate)
        self.add_codestate_with_id(codestate, codestate_id)
        return codestate_id

    def add_codestate_with_id(self, codestate: ContextualCodeStateEntry, codestate_id: str):
        file_path = self.config.codestates_table_path

        if codestate_id in self.written_codestate_ids:
            # If the codestate ID has already been written, skip adding it again
            return

        self.written_codestate_ids.add(codestate_id)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # Write the code state to a CSV file
        with open(file_path, 'a', newline='') as csvfile:
            add_section = self.config.codestates_have_sections

            fieldnames = [Cols.CodeStateID, Cols.Code]
            if add_section:
                fieldnames.append(Cols.CodeStateSection)
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Check if the file is empty to write the header
            if csvfile.tell() == 0:
                writer.writeheader()

            for section in codestate.sections:
                dict = {
                    Cols.CodeStateID: codestate_id,
                    Cols.Code: section.Code,
                }
                if add_section:
                    dict[Cols.CodeStateSection] = section.CodeStateSection
                elif section.CodeStateSection:
                    raise ValueError("CodeStateSection should be None; this dataset does not support sections.")

                writer.writerow(dict)

    def get_codestates_table_path(self):
        # TODO: This and SQL should probably have util functions for reading tables
        # to reduce code duplication
        path = self.config.codestates_table_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"No CSV file found at '{path}'.")
        return path

    def do_codestates_have_sections(self):
        path = self.get_codestates_table_path()
        return pd.read_csv(path, nrows=1).columns.contains(Cols.CodeStateSection)

    def get_codestates_table(self):
        path = self.get_codestates_table_path()
        return pd.read_csv(path)

    def get_codestates_table_subset(self, rows):
        self._check_dataframe_for_codestate_columns(rows)
        table = self.get_codestates_table()
        return table[table[Cols.CodeStateID].isin(rows[Cols.CodeStateID])].copy()

        # This code was for matching on CodeSectionIDs as well, but I don't think
        # we actually want to do that.
        # cols = [Cols.CodeStateID]
        # if Cols.CodeStateSection in rows.columns:
        #     cols.append(Cols.CodeStateSection)
        # merged = pd.merge(table, rows, on=cols)
        # return merged[cols]

class SQLTableCodeStateWriter(CodeStateWriter):

    def __init__(self, context: SQLContext):
        super().__init__()
        self.conn = context.conn
        self._table = None
        self.context = context

    def add_codestate_and_get_id(self, codestate: ContextualCodeStateEntry) -> str:
        codestate_id = self.get_codestate_id_from_hash(codestate)
        self.add_codestate_with_id(codestate, codestate_id)
        return codestate_id

    def get_table(self):
        if self._table is None:
            self._table = self.context.table_manager.get_table(CoreTables.CodeStates)
        return self._table

    def add_codestate_with_id(self, codestate: ContextualCodeStateEntry, codestate_id: str):
        # Defer reading the table in case this is an early call (before initialization)
        table = self.get_table()

        # Execute as a transaction to ensure atomicity
        with self.conn.begin():
            # Check if the code state already exists in the database
            select_statement = table.select().where(
                table.c.CodeStateID == codestate_id
            )
            result = self.conn.execute(select_statement).fetchone()
            if result:
                # TODO: It might be good to check that the stored code state matches
                # the one we are trying to add
                return

            # Add the code state to the CodeStates table using a structured query
            for section in codestate.sections:
                dict = {
                    Cols.CodeStateID: codestate_id,
                    Cols.Code: section.Code,
                }
                if self.context.data_config.codestates_have_sections:
                    dict[Cols.CodeStateSection] = section.CodeStateSection
                elif section.CodeStateSection:
                    raise ValueError("CodeStateSection should be None; this dataset does not support sections.")

                statement = self._table.insert().values(**dict)
                self.conn.execute(statement)

    def do_codestates_have_sections(self):
        table = self.get_table()
        return Cols.CodeStateSection in table.c

    def get_codestates_table(self):
        return pd.read_sql_table(
            CoreTables.CodeStates,
            self.context.conn,
        )

    def get_codestates_table_subset(self, rows: DataFrame) -> DataFrame:
        if not self.context.data_config.sqlalchemy_url.lower().startswith("sqlite://"):
            raise ValueError("This method is only supported for SQLite databases.")

        self._check_dataframe_for_codestate_columns(rows)

        temp_table_name = "temp_ids"
        self._create_temp_id_table(temp_table_name, rows)

        if Cols.CodeStateSection in rows.columns:
            logger.warning("Warning: CodeStateSection column is ignored when fetching subset of CodeStates.\n" \
            "All sections for matching CodeStateIDs will be returned.")

        query = f"""
            SELECT cs.*
            FROM {CoreTables.CodeStates} cs
            JOIN temp_ids temp ON cs.{Cols.CodeStateID} = temp.{Cols.CodeStateID}
        """

        # Join the temporary table with CodeStateIDs to fetch with
        # the CodeStates table.
        return pd.read_sql(query, self.context.conn)

    # Note that right now, we never add sections because we match only
    # on CodeStateID and return all matches. Keeping this as an
    # option as it might be useful later.
    def _create_temp_id_table(self, temp_table_name, rows: DataFrame, add_sections = False) -> DataFrame:
        conn = self.context.conn

        # Remove the table if it exists
        conn.execute(text(f"DROP TABLE IF EXISTS {temp_table_name};"))

        create_query = f"CREATE TEMP TABLE {temp_table_name} ({Cols.CodeStateID} TEXT"
        if add_sections:
            create_query += f", {Cols.CodeStateSection} TEXT"
        create_query += ");"

        # Create a temporary table
        conn.execute(text(create_query))

        # Insert rows
        if add_sections:
            conn.execute(
                text(f"INSERT INTO {temp_table_name} ({Cols.CodeStateID}, {Cols.CodeStateSection}) VALUES (:id, :section);"),
                [{"id": str(id), "section": str(section)} for id, section in rows[[Cols.CodeStateID, Cols.CodeStateSection]].itertuples(index=False)]
            )
        else:
            conn.execute(
                text(f"INSERT INTO {temp_table_name} ({Cols.CodeStateID}) VALUES (:id);"),
                [{"id": str(id)} for id in rows[Cols.CodeStateID].tolist()]
            )



