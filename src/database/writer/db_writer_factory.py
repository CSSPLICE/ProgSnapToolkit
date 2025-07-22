
from abc import ABC, abstractmethod
import os
from database.codestate.git_codestate_writer import GitCodeStateWriter
from database.codestate.directory_codestate_writer import DirectoryCodeStateWriter
from database.codestate.table_codestate_writer import CSVTableCodeStateWriter, SQLTableCodeStateWriter

from sqlalchemy import Connection, create_engine
from database.config import PS2DataConfig, PS2DataWriteConfig
from database.reader.csv_reader import CSVReader
from database.reader.sql_reader import SQLReader
from database.sql_context import IOContext
from database.sql_table_manager import SQLTableManager
from database.writer.sql_writer import SQLContext, SQLWriter
from spec.enums import CodeStateRepresentation
from spec.spec_definition import PS2Versions, ProgSnap2Spec

# TODO: Rename this file

class IOFactory(ABC):
    def __init__(self, db_config: PS2DataConfig, ps2_spec: ProgSnap2Spec = None):
        self.db_config = db_config

        # Temporary PS2 spec and CSR to load metadata
        self.ps2_spec = PS2Versions.load_default()
        self.codestate_representation = CodeStateRepresentation.Table

        if db_config.metadata is None:
            with self.create_reader() as reader:
                self.db_config.metadata = reader.get_metadata_values()

        self.codestate_representation = self.db_config.metadata.CodeStateRepresentation

        if ps2_spec is None:
            version = db_config.metadata.Version if db_config.metadata else None
            if version is None:
                ps2_spec = PS2Versions.load_default()
                print("Warning: No PS2 version specified in metadata, using default version.")
            else:
                ps2_spec = PS2Versions.load_from_string(version)
        self.ps2_spec = ps2_spec

    @abstractmethod
    def create_writer(self) -> "SQLWriterContextManager | CSVIOContextManager":
        pass

    @abstractmethod
    def create_reader(self) -> "SQLReaderContextManager | CSVIOContextManager":
        pass

    def _create_codestate_writer(self, db_config: PS2DataConfig, context: SQLContext):
        if self.codestate_representation == CodeStateRepresentation.Table:
            if db_config.is_csv_config:
                return CSVTableCodeStateWriter(db_config)
            else:
                return SQLTableCodeStateWriter(context)
        elif self.codestate_representation == CodeStateRepresentation.Directory:
            return DirectoryCodeStateWriter(db_config.codestates_dir)
        elif self.codestate_representation == CodeStateRepresentation.Git:
            return GitCodeStateWriter(db_config.codestates_dir)
        else:
            raise ValueError(f"Invalid code state representation: {self.codestate_representation}")

    @classmethod
    def create_factory(cls, db_config: PS2DataConfig, ps2_spec = None) -> "IOFactory":
        if db_config.is_sql_config:
            return SQLIOFactory(db_config, ps2_spec)
        elif db_config.is_csv_config:
            return CSVIOFactory(db_config, ps2_spec)
        raise ValueError(f"Unsupported database configuration type")


class SQLIOFactory(IOFactory):
    def __init__(self, ps2_spec: ProgSnap2Spec, db_config: PS2DataConfig):
        super().__init__(ps2_spec, db_config)
        self.engine = create_engine(db_config.sqlalchemy_url, echo=db_config.echo)
        self.table_manager = SQLTableManager(ps2_spec, db_config)

    def create_writer(self) -> "SQLIOContextManager":
        # Create the root directory if it doesn't exist
        if not isinstance(self.db_config, PS2DataWriteConfig):
            raise ValueError("You must provide a PS2DataWriteConfig for writing.")
        os.makedirs(self.db_config.root_path, exist_ok=True)
        return SQLWriterContextManager(self, False)

    def create_reader(self):
        return SQLReaderContextManager(self, True)

# Use a context manager to handle the connection lifecycle
class SQLIOContextManager(ABC):
    def __init__(self, factory: SQLIOFactory):
        self.factory = factory
        self.conn = None

    def __enter__(self):
        self.conn = self.factory.engine.connect()
        context = SQLContext(
            conn=self.conn,
            table_manager=self.factory.table_manager,
            data_config=self.factory.db_config,
            ps2_spec=self.factory.ps2_spec
        )
        codestate_io = self.factory._create_codestate_writer(self.factory.db_config, context)
        if self.reader:
            return SQLReader(context, codestate_io)
        else:
            return SQLWriter(context, codestate_io)

    def _get_context_and_codestate_io(self):
        context = SQLContext(
            conn=self.conn,
            table_manager=self.factory.table_manager,
            data_config=self.factory.db_config,
            ps2_spec=self.factory.ps2_spec
        )
        codestate_io = self.factory._create_codestate_writer(self.factory.db_config, context)
        return context, codestate_io

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

class SQLReaderContextManager(SQLIOContextManager):
    def __init__(self, factory: SQLIOFactory):
        super().__init__(factory)

    def __enter__(self):
        context, codestate_io = self._get_context_and_codestate_io()
        return SQLReader(context, codestate_io)

class SQLWriterContextManager(SQLIOContextManager):
    def __init__(self, factory: SQLIOFactory):
        super().__init__(factory)

    def __enter__(self):
        context, codestate_io = self._get_context_and_codestate_io()
        return SQLWriter(context, codestate_io)



class CSVIOFactory(IOFactory):
    def __init__(self, ps2_spec: ProgSnap2Spec, db_config: PS2DataConfig):
        super().__init__(ps2_spec, db_config)

    def create_writer(self) -> "CSVIOContextManager":
        raise NotImplementedError("CSV writer not implemented.")

    def create_reader(self):
        return CSVIOContextManager(self)

class CSVIOContextManager:

    def __init__(self, factory: CSVIOFactory):
        self.factory = factory

    def __enter__(self):
        context = IOContext(
            data_config=self.factory.db_config,
            ps2_spec=self.factory.ps2_spec
        )
        codestate_io = self.factory._create_codestate_writer(self.factory.db_config, None)
        return CSVReader(context, codestate_io)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # No explicit cleanup needed for CSVReader
        pass