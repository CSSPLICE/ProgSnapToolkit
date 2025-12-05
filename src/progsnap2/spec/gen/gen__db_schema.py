
from progsnap2.spec.spec_definition import ProgSnap2Spec, Requirement


def generate_main_table_schema(spec: ProgSnap2Spec) -> str:
    """Generates a JSON object defining the SQL(ite) schema for
    the main table based on the provided ProgSnap2Spec.
    """
    import json

    columns = []
    for column in spec.main_table.columns:
        datatype = column.datatype
        col_def = {
            "name": column.name,
            "datatype": {
                # Null types are for enums
                "type": datatype.typescript_type or 'string',
                "max_str_length": datatype.max_str_length.value if datatype.max_str_length is not None else None
            },
            "nullable": not column.requirement != Requirement.Required,
            "description": column.description
        }
        if column.datatype == "String" and column.length:
            col_def["length"] = column.length
        columns.append(col_def)

    schema = {
        "table_name": "MainTable",
        "columns": columns,
    }

    return json.dumps(schema, indent=4)

def generate_codestates_table_schema(spec: ProgSnap2Spec) -> str:
    """Generates a JSON object defining the SQL(ite) schema for
    the codestates table based on the provided ProgSnap2Spec.
    """
    import json

    columns = [
        {
            "name": "CodeStateID",
            "datatype": {
                "type": "string",
                "max_str_length": "ID"
            },
            "nullable": False,
            "description": "Unique identifier for the code state."
        },
        {
            "name": "Code",
            "datatype": {
                "type": "text",
                "max_str_length": None
            },
            "nullable": False,
            "description": "The actual code content."
        },
        {
            "name": "CodeStateSection",
            "datatype": {
                "type": "string",
                "max_str_length": "Path"
            },
            "nullable": True,
            "description": "The section of the code state."
        }
    ]

    schema = {
        "table_name": "CodeStates",
        "columns": columns,
    }

    return json.dumps(schema, indent=4)