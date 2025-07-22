import csv
from sqlalchemy import insert
from database.codestate.codestate_writer import ContextualCodeStateEntry, CodeStateWriter
from database.config import PS2DataWriteConfig
from database.sql_context import IOContext, SQLContext
from spec.enums import CodeStatesTableColumns as Cols
import os

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

class SQLTableCodeStateWriter(CodeStateWriter):

    def __init__(self, context: SQLContext):
        super().__init__()
        self.conn = context.conn
        self.table = context.table_manager.codestates_table

    def add_codestate_and_get_id(self, codestate: ContextualCodeStateEntry) -> str:
        codestate_id = self.get_codestate_id_from_hash(codestate)
        self.add_codestate_with_id(codestate, codestate_id)
        return codestate_id

    def add_codestate_with_id(self, codestate: ContextualCodeStateEntry, codestate_id: str):
        # Execute as a transaction to ensure atomicity
        with self.conn.begin():
            # Check if the code state already exists in the database
            select_statement = self.table.select().where(
                self.table.c.CodeStateID == codestate_id
            )
            result = self.conn.execute(select_statement).fetchone()
            if result:
                # TODO: It might be good to check that the stored code state matches
                # the one we are trying to add
                return

            dict = {
                Cols.CodeStateID: codestate_id,
                Cols.Code: section.Code,
            }
            if self.context.data_config.codestates_have_sections:
                dict[Cols.CodeStateSection] = section.CodeStateSection
            elif section.CodeStateSection:
                raise ValueError("CodeStateSection should be None; this dataset does not support sections.")

            # Add the code state to the CodeStates table using a structured query
            for section in codestate.sections:
                statement = self.table.insert().values(**dict)
                self.conn.execute(statement)



