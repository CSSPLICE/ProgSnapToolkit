# server/main.py
from enum import Enum
import os
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Type

from fastapi.responses import JSONResponse, PlainTextResponse

from api.config import PS2APIConfig
from api.models import TempCodeStateEntry
from database.writer.sql_writer import SQLWriter
from api.events import DataModelGenerator
from database.writer.db_writer import DBWriter, LogResult
from database.writer.db_writer_factory import IOFactory, SQLIOFactory
from spec.spec_definition import PS2Versions, ProgSnap2Spec
from spec.gen.gen_client import generate_ts_methods

file_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(file_dir, "..")

spec = PS2Versions.v1_0.load()

data_model_gen = DataModelGenerator(spec)
MainTableEvent = data_model_gen.MainTableEvent
AnyAdditionalColumns = data_model_gen.AnyAdditionalColumns


api_config = PS2APIConfig.from_yaml(os.path.join(src_dir, "api/api_config.yaml"), spec)

db_writer_factory: SQLIOFactory = IOFactory.create_factory(api_config.database_config, spec=spec)

with db_writer_factory.create_writer() as writer:
    # Create the tables in the database
    writer.initialize_database()

# For use in Depends
def create_writer():
    with db_writer_factory.create_writer() as writer:
        yield writer



app = FastAPI()

cors_config = api_config.cors_config

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.allow_origins,
    allow_credentials=cors_config.allow_credentials,
    allow_methods=cors_config.allow_methods,
    allow_headers=cors_config.allow_headers,
)

# TODO: Would be nice if CORS worked when there's an error
# But it seems like the headers don't get added here
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# I don't think this is needed (or the whole type), but I'll keep for now
@app.get("/placeholder")
def get_additional_column_types(additionalColumns: AnyAdditionalColumns): # type: ignore
    """
    Placeholder endpoint to get the additional column types.
    """
    pass

@app.post("/events_with_code_states", operation_id="addEventsWithCodeStates", response_model=LogResult)
def add_events_with_code_states(events: List[MainTableEvent], code_states: List[TempCodeStateEntry], writer: SQLWriter = Depends(create_writer)): # type: ignore
    """
    Add events and code states to the database at the same time to ensure consistency.

    Note: TempCodeState.code_state_id is a temporary ID that will be remapped when logging
    the events. It is used to map multiple events to the same code state in this request.
    """
    events = [event.model_dump(exclude_none=True) for event in events]
    if api_config.add_server_timestamps:
        writer.add_server_timestamps(events)

    code_states = {code_state.temp_codestate_id: code_state for code_state in code_states}
    return writer.add_events_with_codestates(events, code_states)

@app.get("/generate_api_helper", operation_id="generateAPIHelper", response_class=PlainTextResponse)
def generate_api_helper() -> str:
    return generate_ts_methods(spec)