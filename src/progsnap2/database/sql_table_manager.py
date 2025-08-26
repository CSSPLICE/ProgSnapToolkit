
from abc import ABC, abstractmethod
from progsnap2.database.config import PS2DataConfig, PS2DataWriteConfig
from progsnap2.spec.enums import CodeStateRepresentation
from progsnap2.spec.spec_definition import ProgSnap2Spec

from datetime import datetime
from sqlalchemy import Connection, Engine, Index, MetaData, Table, Column as SQLColumn, Integer, String, Float, Enum as SQLEnum, UniqueConstraint, inspect
from sqlalchemy.dialects.sqlite import DATETIME

from progsnap2.spec.datatypes import DBStringLength, PS2Datatype
from progsnap2.spec.spec_definition import ProgSnap2Spec, Property, Requirement, Column as SpecColumn
from progsnap2.spec.enums import CodeStatesTableColumns as CodeCols, MainTableColumns as Cols, CoreTables

from sqlalchemy import Text, String, Integer, Float, Boolean

class SQLTableManager(ABC):

    def __init__(self, metadata: MetaData):
        self._metadata = metadata
        self.table_names = self._metadata.tables.keys()

    def get_table(self, table_name: str) -> Table:
        if table_name not in self.table_names:
            raise ValueError(f"Table {table_name} does not exist in the database.")
        return self._metadata.tables[table_name]

class SQLReaderTableManager(SQLTableManager):
    def __init__(self, engine: Engine):
        metadata = MetaData()
        metadata.reflect(bind=engine)
        super().__init__(metadata)
        self.engine = engine


class SQLWriterTableManager(SQLTableManager):
    def __init__(self, spec: ProgSnap2Spec, db_config: PS2DataWriteConfig):
        self.metadata_values = db_config.metadata
        self.spec = spec
        self.db_config = db_config
        self._sql_metadata: MetaData = None
        self.main_table: Table = None
        self.link_tables: dict[str, Table] = {}
        self.metadata_table: Table = None
        self.codestates_table: Table = None

        self._define_tables()

    def has_codestates_table(self) -> bool:
        """
        Check if the codestates table is defined.
        """
        return self.codestates_table is not None

    def have_tables_been_created(self, conn: Connection) -> bool:
        """
        Check if tables have already been created.
        Note: this does not check whether tables are out of date.
        """
        return inspect(conn.engine).has_table(self.metadata_table.name)


    def map_datatype(self, datatype: PS2Datatype):
        """
        Maps ProgSnap2 datatype strings to SQLAlchemy column types.
        Expand this as needed for more precise typing or databases.
        """

        if datatype.max_str_length is not None:
            if datatype.max_str_length == DBStringLength.Short:
                return String(self.db_config.short_str_length)
            elif datatype.max_str_length == DBStringLength.Path:
                return String(self.db_config.path_str_length)

        if datatype.python_type == str:
            # If the datatype is a string but has no max length, use Text
            return Text

        # Convert python type to SQL type
        type_map = {
            int: Integer,
            float: Float,
            bool: Boolean,
            # Currently unused, since it doesn't support timezone
            # datetime: DATETIME(timezone=True),
        }
        if datatype.python_type not in type_map:
            raise ValueError(f"Unconvertible datatype: {datatype.python_type}")

        return type_map.get(datatype.python_type)



    def define_column(self, column_spec: SpecColumn):
        """
        Define a SQLAlchemy column based on the column spec.
        """
        required = column_spec.requirement == Requirement.Required
        col_type = self.map_datatype(column_spec.datatype)
        kwargs = {
            'nullable': not required,
            'doc': column_spec.description
        }
        return SQLColumn(column_spec.name, col_type, **kwargs)


    def _define_tables(self):
        self._sql_metadata = metadata = MetaData()
        spec = self.spec

        # --- Metadata Table ---
        self.metadata_table = Table(
            CoreTables.Metadata, metadata,
            SQLColumn("Property", String(255), nullable=False),
            # Value has various datatypes, so we'll store all al strings
            SQLColumn("Value", String(2048), nullable=False)
        )

        # --- Main Table ---
        main_columns = []

        for col in spec.main_table.columns:
            main_columns.append(self.define_column(col))

        self.main_table = Table(
            CoreTables.MainTable, metadata,
            *main_columns
        )

        id_datatype = self.map_datatype(PS2Datatype.ID)
        path_datatype = self.map_datatype(PS2Datatype.RelativePath)

        for link_table in spec.link_tables:
            columns = []
            # ID columns
            for id_col in link_table.id_column_names:
                columns.append(SQLColumn(id_col, id_datatype, nullable=False))
            # Additional columns
            for add_col in link_table.additional_columns:
                columns.append(self.define_column(add_col))

            tbl = Table(
                link_table.name, metadata,
                *columns
            )
            self.link_tables[link_table.name] = tbl

        if self.metadata_values.CodeStateRepresentation == CodeStateRepresentation.Table:
            cols_etc = [
                SQLColumn(CodeCols.CodeStateID, id_datatype, nullable=False),
            ]
            if self.db_config.codestates_have_sections:
                cols_etc.append(SQLColumn(CodeCols.CodeStateSection, path_datatype, nullable=True))
            cols_etc.extend([
                SQLColumn(CodeCols.Code, Text(), nullable=False),
                UniqueConstraint(CodeCols.CodeStateID, CodeCols.CodeStateSection, name="uq_codestate_id_section"),
                Index("ix_codestate_id", CodeCols.CodeStateID),
            ])

            self.codestates_table = Table(
                CoreTables.CodeStates, metadata,
                *cols_etc
            )

    def create_tables(self, conn: Connection):
        self._sql_metadata.create_all(conn)

    def update_tables(self, conn: Connection):
        """
        Update the tables in the database to match the current spec.
        Learns the current structure from the connection, and then
        iterates through each table defined in our spec-defined metadata
        and adds any missing columns. Should not delete tables or columns.
        """

        # Get the current structure of the database
        current_metadata = MetaData(bind=conn)
        current_metadata.reflect()

        # Iterate through each table defined in our spec-defined metadata
        for table_name, table in self.link_tables.items():
            # Check if the table exists in the current metadata
            if table_name in current_metadata.tables:
                # If it exists, check for missing columns
                existing_table = current_metadata.tables[table_name]
                self._update_table_columns(conn, existing_table, table)
            else:
                # If the table doesn't exist, create it
                table.create(conn)

    def _update_table_columns(self, conn: Connection, current_table: Table, new_table: Table):
        """
        Update the columns of a table in the database to match the new table.
        """
        for column in new_table.columns:
            if column.name not in current_table.columns:
                # If the column is missing, add it to the existing table
                column.create(current_table)
            if column.type != current_table.columns[column.name].type:
                # If the column type is different, alter the column
                raise NotImplementedError(
                    f"""Column type change not implemented for {column.name} in {current_table.name}.
                    Please update the database manually."""
                )

    def update_metadata_values(self, conn: Connection):
        """
        Update the metadata values in the database.
        """
        # Clear existing metadata values
        conn.execute(self.metadata_table.delete())

        metadata_dict = self.metadata_values.model_dump()
        print(f"Updating metadata values: {len(metadata_dict)}")

        # Insert new metadata values
        for property, value in metadata_dict.items():
            print(f"Inserting metadata: {property} = {value}")
            conn.execute(self.metadata_table.insert().values(Property=property, Value=value))

        conn.commit()
