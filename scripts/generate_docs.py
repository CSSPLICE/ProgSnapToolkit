import os, sys

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(root_path, "src")
sys.path.insert(0, src_path)

from progsnap2.spec.gen.gen_docs import render_spec
from progsnap2.spec.spec_definition import PS2Versions

docs_path = os.path.join(root_path, "docs", "specs")

for version in PS2Versions:
    spec = version.load()
    markdown = render_spec(spec)
    paths = [os.path.join(docs_path, f"ProgSnap2-v{spec.version}.md")]
    # if version.value.default:
    #     paths.append(os.path.join(docs_path, "ProgSnap2.md"))
    for path in paths:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding='utf-8') as f:
            f.write(markdown)
