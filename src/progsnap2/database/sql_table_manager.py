import logging
logger = logging.getLogger(__name__)

from abc import ABC, abstractmethod
from progsnap2.database.config import PS2DataConfig, PS2DataWriteConfig
from progsnap2.spec.enums import CodeStateRepresentation
from progsnap2.spec.spec_definition import ProgSnap2Spec

from datetime import datetime
from sqlalchemy import Connection, Engine, Index, MetaData, Table, Column as SQLColumn, Integer, String, Float, Enum as SQLEnum, UniqueConstraint, inspect, text
from sqlalchemy.dialects.sqlite import DATETIME
from sqlalchemy.orm import Session

from progsnap2.spec.datatypes import MAX_STRING_LENGTH, DBStringLength, PS2Datatype
from progsnap2.spec.spec_definition import ProgSnap2Spec, Property, Requirement, Column as SpecColumn
from progsnap2.spec.enums import CodeStatesTableColumns as CodeCols, MainTableColumns as Cols, CoreTables

from sqlalchemy import Text, String, Integer, Float, Boolean

class SQLTableManager(ABC):

    def __init__(self, metadata: MetaData):
        self._metadata = metadata
        self.table_names = self._metadata.tables.keys()

    def get_table(self, table_name: str) -> Table:
        table_name = table_name.lower()
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
        self.main_table: Table = None
        self.link_tables: dict[str, Table] = {}
        self.metadata_table: Table = None
        self.codestates_table: Table = None

        metadata = self._create_metadata()
        super().__init__(metadata)

    def has_codestates_table(self) -> bool:
        """
        Check if the codestates table is defined.
        """
        return self.codestates_table is not None

    def have_tables_been_created(self, session: Session) -> bool:
        """
        Check if tables have already been created.
        Note: this does not check whether tables are out of date.
        """
        # Typically a bad practice to get the connection, but this is only
        # called one at load time, so should be ok...
        metadata = inspect(session.connection().engine)
        return metadata.has_table(self.metadata_table.name) and metadata.has_table(self.main_table.name)


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
            return Text(MAX_STRING_LENGTH)

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



    def define_column(self, column_spec: SpecColumn, indexed_column_names: list[str] = []):
        """
        Define a SQLAlchemy column based on the column spec.
        """
        indexed_column_names = [name.lower() for name in indexed_column_names]
        required = column_spec.requirement == Requirement.Required
        col_type = self.map_datatype(column_spec.datatype)
        indexed = column_spec.name.lower() in indexed_column_names
        kwargs = {
            'nullable': not required,
            'doc': column_spec.description
        }
        if indexed:
            kwargs['index'] = True
        return SQLColumn(column_spec.name, col_type, **kwargs)


    def _create_metadata(self):
        metadata = MetaData()
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

        main_table_column_names = [col.name.lower() for col in spec.main_table.columns]
        indexed_column_names = [col.lower() for col in self.db_config.indexed_columns]
        for col in indexed_column_names:
            if col not in main_table_column_names:
                raise ValueError(f"Indexed column {col} not found in main table columns.")

        for col in spec.main_table.columns:
            main_columns.append(self.define_column(col, indexed_column_names))

        self.main_table = Table(
            CoreTables.MainTable, metadata,
            *main_columns
        )

        id_datatype = self.map_datatype(PS2Datatype.ID)
        path_datatype = self.map_datatype(PS2Datatype.RelativePath)

        for link_table in spec.link_tables:
            link_table_name_lc = link_table.name.lower()
            columns = []
            # ID columns
            for id_col in link_table.id_column_names:
                columns.append(SQLColumn(id_col, id_datatype, nullable=False))
            # Additional columns
            for add_col in link_table.additional_columns:
                columns.append(self.define_column(add_col))
            for uq_cols in link_table.unique_constraints:
                columns.append(UniqueConstraint(*uq_cols, name=f"uq_{link_table_name_lc}_{'_'.join(uq_cols)}"))

            tbl = Table(
                link_table_name_lc, metadata,
                *columns
            )
            self.link_tables[link_table_name_lc] = tbl

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

        return metadata

    def create_tables(self, session: Session):
        # Creates a connection, since we need metadata
        # Ok, since we only call it once
        self._metadata.create_all(session.connection())

    def update_tables(self, session: Session):
        """
        Update the tables in the database to match the current spec.
        Learns the current structure from the connection, and then
        iterates through each table defined in our spec-defined metadata
        and adds any missing columns. Should not delete tables or columns.
        """

        conn = session.connection()

        # Get the current structure of the database
        current_metadata = MetaData()
        current_metadata.reflect(bind=conn.engine)

        tables = {
            CoreTables.Metadata: self.metadata_table,
            CoreTables.MainTable: self.main_table,
            CoreTables.CodeStates: self.codestates_table
        }
        tables.update(self.link_tables)

        # Iterate through each table defined in our spec-defined metadata
        for table_name, table in tables.items():
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
            logger.info(f"--- Checking column {column.name} in table {current_table.name}")
            if column.name not in current_table.columns:
                logger.info(f"--- Adding column {column.name} to table {current_table.name}")
                # If the column is missing, add it to the existing table
                query = f"""ALTER TABLE {current_table.name} ADD COLUMN {column.name} {column.type}"""
                conn.execute(text(query))
            elif str(column.type) != str(current_table.columns[column.name].type):
                if str(column.type).startswith("TEXT(") or str(column.type).startswith("VARCHAR("):
                    logger.warning(f"""Cannot verify TEXT length changes. Please verify manually if needed:
                                   {column.type} (new) != {current_table.columns[column.name].type} (old).""")
                    continue
                # If the column type is different, alter the column
                raise NotImplementedError(
                    f"""Column type change not implemented for {column.name} in {current_table.name}.
                    {column.type} (new) != {current_table.columns[column.name].type} (old).
                    Please update the database manually."""
                )

    def update_metadata_values(self, session: Session):
        """
        Update the metadata values in the database.
        """
        # Clear existing metadata values
        session.execute(self.metadata_table.delete())

        metadata_dict = self.metadata_values.model_dump()
        logger.info(f"Updating metadata values: {len(metadata_dict)}")

        # Insert new metadata values
        for property, value in metadata_dict.items():
            logger.info(f"Inserting metadata: {property} = {value}")
            session.execute(self.metadata_table.insert().values(Property=property, Value=value))

        session.commit()
