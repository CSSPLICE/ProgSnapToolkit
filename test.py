import os, sys

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, src_path)

from sqlalchemy import create_engine
from progsnap2.spec.gen.gen_client import generate_ts_methods
from progsnap2.spec.gen.gen_enums import generate_enums_for_spec
from progsnap2.spec.gen.gen__db_schema import generate_codestates_table_schema, generate_main_table_schema as generate_main_table_schema
from progsnap2.spec.spec_definition import PS2Versions, ProgSnap2Spec
from progsnap2.spec.enums import EventType
import pyperclip

if __name__ == "__main__":
    # Load schema
    schema = ProgSnap2Spec.from_yaml("src/provena/progsnap2-provena.yaml")
    # schema = PS2Versions.v1_0.load()

    out = generate_enums_for_spec(schema)
    with open("toolbox/src/progsnap2/spec/enums.py", "w", encoding='utf-8') as f:
        f.write(out)

    out = generate_ts_methods(schema)
    pyperclip.copy(out)

    # out = generate_main_table_schema(schema)
    # out = generate_codestates_table_schema(schema)
    # print(out)


    # Connect to database
    # engine = create_engine("sqlite:///example.db", echo=True)

    # Create tables
    # create_tables_from_schema(schema, engine)