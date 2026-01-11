import logging
logger = logging.getLogger(__name__)

from abc import ABC, abstractmethod
import os
from progsnap2.database.codestate.git_codestate_writer import GitCodeStateWriter
from progsnap2.database.codestate.directory_codestate_writer import DirectoryCodeStateWriter
from progsnap2.database.codestate.table_codestate_writer import CSVTableCodeStateWriter, SQLTableCodeStateWriter
from progsnap2.database.codestate.keystroke_codestate_writer import KeystrokeCodestateIO

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from progsnap2.database.config import PS2DataConfig, PS2DataWriteConfig
from progsnap2.database.reader.csv_reader import CSVReader
from progsnap2.database.reader.sql_reader import SQLReader
from progsnap2.database.sql_context import IOContext
from progsnap2.database.sql_table_manager import SQLReaderTableManager, SQLWriterTableManager
from progsnap2.database.writer.sql_writer import SQLContext, SQLWriter
from progsnap2.spec.enums import CodeStateRepresentation
from progsnap2.spec.spec_definition import PS2Versions, ProgSnap2Spec

# TODO: Rename this file
# Also, long-term, this should probably be split into two classes,
# one for reading and one for writing. There's just no use case for
# doing both at once and the code is becoming too conditional.

class IOFactory(ABC):
    def __init__(self, db_config: PS2DataConfig, ps2_spec: ProgSnap2Spec = None):
        self.db_config = db_config

        # Temporary PS2 spec and CSR to load metadata
        self.ps2_spec = PS2Versions.load_default() if ps2_spec is None else ps2_spec
        self.codestate_representation = CodeStateRepresentation.Table

    # Must be called after child initialization
    # TODO: Maybe init should be an abstract method? Call it then then?
    def load_metadata_and_spec(self, ps2_spec: ProgSnap2Spec):
        db_config = self.db_config
        if db_config.metadata is None:
            with self.create_reader() as reader:
                db_config.metadata = reader.get_metadata_values()

        self.codestate_representation = db_config.metadata.CodeStateRepresentation

        if ps2_spec is None:
            version = db_config.metadata.Version
            if version is None:
                logger.warning("Warning: No PS2 spec version found in metadata. Using default spec.")
                self.ps2_spec = PS2Versions.load_default()
            else:
                try:
                    self.ps2_spec = PS2Versions.load_from_string(version)
                except:
                    default_spec = PS2Versions.load_default()
                    logger.warning(f"Warning: Unable to load PS2 spec for version '{version}'. Using default spec: {default_spec.version}.")
                    self.ps2_spec = default_spec

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
        elif self.codestate_representation == CodeStateRepresentation.Keystroke:
            return KeystrokeCodestateIO()
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
    def __init__(self, db_config: PS2DataConfig, ps2_spec: ProgSnap2Spec):
        super().__init__(db_config, ps2_spec)
        url = db_config.sqlalchemy_url
        if not url:
            raise ValueError("SQLAlchemy URL is not set in the database configuration.")

        if url.lower().startswith("sqlite://"):
            file = url[10:]  # Remove 'sqlite://' prefix
            if not os.path.exists(file):
                logger.warning(f"Warning: SQLite database file '{file}' does not exist.")

        self.engine = create_engine(
            db_config.sqlalchemy_url,
            echo=db_config.echo,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_timeout=db_config.pool_timeout,
            pool_recycle=db_config.pool_recycle
        )
        try:
            self.table_names = inspect(self.engine).get_table_names()
        except Exception:
            self.table_names = None
        self.table_manager = None # Don't need/want this for reading
        self.load_metadata_and_spec(ps2_spec)

    def create_writer(self) -> "SQLIOContextManager":
        # Create the root directory if it doesn't exist
        if not isinstance(self.db_config, PS2DataWriteConfig):
            raise ValueError("You must provide a PS2DataWriteConfig for writing.")
        if self.table_manager is None:
            self.table_manager = SQLWriterTableManager(self.ps2_spec, self.db_config)
        os.makedirs(self.db_config.root_path, exist_ok=True)
        return SQLWriterContextManager(self)

    def create_reader(self):
        if self.table_manager is None:
            self.table_manager = SQLReaderTableManager(self.engine)
        return SQLReaderContextManager(self)

# Use a context manager to handle the session lifecycle
class SQLIOContextManager(ABC):
    def __init__(self, factory: SQLIOFactory):
        self.factory = factory
        self.session = None

    @abstractmethod
    def __enter__(self):
        pass

    def _get_context_and_codestate_io(self):
        # Could use a sessionmaker if I have more config
        # or need to create sessions in multiple places
        self.session = Session(bind=self.factory.engine)
        context = SQLContext(
            session=self.session,
            table_manager=self.factory.table_manager,
            data_config=self.factory.db_config,
            ps2_spec=self.factory.ps2_spec
        )
        codestate_io = self.factory._create_codestate_writer(self.factory.db_config, context)
        return context, codestate_io

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()

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
        self.load_metadata_and_spec(ps2_spec)

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