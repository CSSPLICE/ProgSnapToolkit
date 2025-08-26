from dataclasses import dataclass

import pytest
from progsnap2.api.events import DataModelGenerator
from progsnap2.spec.spec_definition import ProgSnap2Spec, PS2Versions

@dataclass
class SpecConfig:
    spec: ProgSnap2Spec
    MainTableEvent: type

@pytest.fixture(scope="session")
def config():
    spec = PS2Versions.v1_0.load()
    data_model_gen = DataModelGenerator(spec)
    MainTableEvent = data_model_gen.MainTableEvent

    return SpecConfig(spec=spec, MainTableEvent=MainTableEvent)