

import os
from progsnap2.spec.gen.gen_docs import render_main_table_columns, render_metadata_section, render_property, render_spec


def test_doc_generator(config):
    # doc = render_metadata_section(config.spec)
    doc = render_spec(config.spec)

    file = "test_data/doc.md"
    if os.path.exists(file):
        os.remove(file)
    else:
        os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w") as f:
        f.write(doc)