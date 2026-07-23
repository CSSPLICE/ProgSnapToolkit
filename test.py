import os, sys

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, src_path)

from progsnap2.spec.gen.gen_client import generate_ts_methods
from progsnap2.spec.gen.gen_enums import generate_enums_for_spec
from progsnap2.spec.gen.gen__db_schema import generate_codestates_table_schema, generate_main_table_schema
from progsnap2.spec.spec_definition import PS2Versions
import pyperclip

if __name__ == "__main__":
    # Load schema
    schema = PS2Versions.v1_0.load()

    out = generate_enums_for_spec(schema)
    with open("src/progsnap2/spec/enums.py", "w", encoding='utf-8') as f:
        f.write(out)

    out = generate_ts_methods(schema)
    pyperclip.copy(out)

    # out = generate_main_table_schema(schema)
    # out = generate_codestates_table_schema(schema)
    # print(out)
