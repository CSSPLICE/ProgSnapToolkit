import os, sys

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, src_path)

from sqlalchemy import create_engine
from progsnap2.spec.gen.gen_client import generate_ts_methods
from progsnap2.spec.gen.gen_enums import generate_enums_for_spec
from progsnap2.spec.spec_definition import PS2Versions, ProgSnap2Spec
from progsnap2.spec.enums import EventType

if __name__ == "__main__":
    # Load schema
    schema = PS2Versions.v1_0.load()

    out = generate_enums_for_spec(schema)
    with open("src/spec/enums.py", "w", encoding='utf-8') as f:
        f.write(out)

    out = generate_ts_methods(schema)
    # print(out)

    # Connect to database
    # engine = create_engine("sqlite:///example.db", echo=True)

    # Create tables
    # create_tables_from_schema(schema, engine)