
from abc import ABC, abstractmethod
import os
from database.codestate.git_codestate_writer import GitCodeStateWriter
from database.codestate.directory_codestate_writer import DirectoryCodeStateWriter
from database.codestate.table_codestate_writer import CSVTableCodeStateWriter, SQLTableCodeStateWriter

from sqlalchemy import Connection, create_engine
from database.config import PS2DataConfig
from database.reader.csv_reader import CSVReader
from database.reader.sql_reader import SQLReader
from database.sql_context import IOContext
from database.sql_table_manager import SQLTableManager
from database.writer.sql_writer import SQLContext, SQLWriter
from spec.enums import CodeStateRepresentation
from spec.spec_definition import PS2Versions, ProgSnap2Spec

# TODO: Rename this file

class IOFactory(ABC):
    def __init__(self, ps2_spec: ProgSnap2Spec, db_config: PS2DataConfig):
        self.ps2_spec = ps2_spec
        self.db_config = db_config

    @abstractmethod
    def create_writer(self):
        pass

    @abstractmethod
    def create_reader(self):
        pass

    def _create_codestate_writer(self, db_config: PS2DataConfig, context: SQLContext):
        # TODO: These aren't actually the same enum right now... so need to str convert
        code_state_representation = str(self.db_config.metadata.CodeStateRepresentation)
        if code_state_representation == CodeStateRepresentation.Table:
            if db_config.is_csv_config:
                return CSVTableCodeStateWriter(db_config)
            else:
                return SQLTableCodeStateWriter(context)
        elif code_state_representation == CodeStateRepresentation.Directory:
            return DirectoryCodeStateWriter(db_config.codestates_dir)
        elif code_state_representation == CodeStateRepresentation.Git:
            return GitCodeStateWriter(db_config.codestates_dir)
        else:
            raise ValueError(f"Invalid code state representation: {code_state_representation}")

    @classmethod
    def create_factory(cls, db_config: PS2DataConfig, ps2_spec = None) -> "IOFactory":
        if ps2_spec is None:
            version = db_config.metadata.Version
            if version is None:
                ps2_spec = PS2Versions.load_default()
                print("Warning: No PS2 version specified in metadata, using default version.")
            else:
                ps2_spec = PS2Versions.load_from_string(version)
        if db_config.is_sql_config:
            return SQLIOFactory(ps2_spec, db_config)
        elif db_config.is_csv_config:
            return CSVIOFactory(ps2_spec, db_config)
        raise ValueError(f"Unsupported database configuration type")


class SQLIOFactory(IOFactory):
    def __init__(self, ps2_spec: ProgSnap2Spec, db_config: PS2DataConfig):
        super().__init__(ps2_spec, db_config)
        self.engine = create_engine(db_config.sqlalchemy_url, echo=db_config.echo)
        self.table_manager = SQLTableManager(ps2_spec, db_config)

    def create_writer(self) -> "SQLIOContextManager":
        # Create the root directory if it doesn't exist
        os.makedirs(self.db_config.root_path, exist_ok=True)
        return SQLIOContextManager(self, False)

    def create_reader(self):
        return SQLIOContextManager(self, True)

# Use a context manager to handle the connection lifecycle
class SQLIOContextManager:
    def __init__(self, factory: SQLIOFactory, reader: bool):
        self.factory = factory
        self.conn = None
        self.reader = reader

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

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

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