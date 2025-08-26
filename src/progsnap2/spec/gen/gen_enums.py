
from spec.spec_definition import LinkTableSpec, ProgSnap2Spec, EnumType, Column
import keyword


def generate_enums_for_spec(spec: ProgSnap2Spec):
    """
    Generate python enum code from a ProgSnap2 spec.
    """
    sections = []
    sections.append(_generate_imports())
    sections.append(_generate_core_tables_enum())
    sections.append(_generate_code_state_columns_enum())
    sections.append(_generate_metadata_properties_enum(spec))
    sections.append(_generate_main_table_columns_enum(spec))
    sections.append(_generate_event_type_enum(spec))
    sections.append(_generate_link_table_names_enum(spec))

    for link_table in spec.link_tables:
        sections.append(generate_link_table_columns_enum(link_table, spec))

    for enum_type in spec.enum_types:
        sections.append(generate_defined_enum(enum_type))

    return "\n\n".join(sections)

def _generate_imports() -> str:
    """
    Generate the import statements for the enums.
    """
    return "from enum import Enum"

def format_docstring(doc: str, indent: str) -> str:
    """
    Format the docstring for the enum.
    """
    if '\n' not in doc:
        return f"{indent}\"\"\"{doc}\"\"\"\n"
    lines = doc.split('\n')
    formatted_lines = ["" if line.strip() == "" else f"{indent}{line}" for line in lines]
    if formatted_lines[-1].strip() == "":
        formatted_lines.pop()
    return f'{indent}"""\n' + "\n".join(formatted_lines) + f'\n{indent}"""' + "\n\n"


def generate_enum(enum_name: str, enum_values: list[str], doc: str = None, docs: list[str] = None) -> str:
    enum_str = f"class {enum_name}(str, Enum):\n"
    if doc:
        enum_str += format_docstring(doc, "    ")
    for value, value_doc in zip(enum_values, docs or [None] * len(enum_values)):
        key = value.replace('.', '').replace('-', '_').replace(' ', '_')
        if key in keyword.kwlist:
            key = f"{key}_"
        enum_str += f"    {key} = '{value}'\n"
        if value_doc:
            enum_str += format_docstring(value_doc, "    ")
    enum_str += "    def __str__(self):\n"
    enum_str += "        return self.value\n"
    return enum_str


def _generate_core_tables_enum() -> str:
    enum_name = "CoreTables"
    enum_values = ["MainTable", "Metadata", "CodeStates"]
    doc = "Primary tables in the database."
    return generate_enum(enum_name, enum_values, doc)

def _generate_code_state_columns_enum() -> str:
    """
    Generate python enum code from a ProgSnap2 code state columns.
    """
    enum_name = "CodeStatesTableColumns"
    # TODO: At some point might want to allow additional ones
    # Could even just define this as a link table...
    # But some parts of it have to be standardized
    enum_values = ["CodeStateID", "Code", "CodeStateSection"]
    doc = "Valid columns for the CodeStates table."
    return generate_enum(enum_name, enum_values, doc)


def generate_defined_enum(enum_type: EnumType) -> str:
    """
    Generate python enum code from a ProgSnap2 enum type.
    """
    enum_name = enum_type.name
    enum_values = [value.name for value in enum_type.values]
    docs = [value.description for value in enum_type.values]
    return generate_enum(enum_name, enum_values, None, docs)

def _generate_metadata_properties_enum(spec: ProgSnap2Spec) -> str:
    """
    Generate python enum code from a ProgSnap2 metadata properties.
    """
    enum_name = "MetadataProperties"
    enum_values = [property.name for property in spec.metadata.properties]
    doc = "Valid properties for the metadata table."
    docs = [property.description for property in spec.metadata.properties]
    return generate_enum(enum_name, enum_values, doc, docs)

def _generate_main_table_columns_enum(spec: ProgSnap2Spec) -> str:
    """
    Generate python enum code from a ProgSnap2 main table columns.
    """
    enum_name = "MainTableColumns"
    enum_values = [column.name for column in spec.main_table.columns]
    doc = "Valid columns for the MainTable."
    docs = [column.description for column in spec.main_table.columns]
    return generate_enum(enum_name, enum_values, doc, docs)

def _generate_event_type_enum(spec: ProgSnap2Spec) -> str:
    """
    Generate python enum code from a ProgSnap2 event types.
    """
    enum_name = "EventType"
    enum_values = [event_type.name for event_type in spec.main_table.event_types]
    doc = "Possible values for the EventType columns of the MainTable."
    docs = [event_type.description for event_type in spec.main_table.event_types]
    return generate_enum(enum_name, enum_values, doc, docs)

def _generate_link_table_names_enum(spec: ProgSnap2Spec) -> str:
    """
    Generate python enum code from a ProgSnap2 link table names.
    """
    enum_name = "LinkTableNames"
    enum_values = [link_table.name for link_table in spec.link_tables]
    doc = "Defined LinkTables"
    docs = [link_table.description for link_table in spec.link_tables]
    return generate_enum(enum_name, enum_values, doc, docs)

def generate_link_table_columns_enum(link_table_spec: LinkTableSpec, ps2_spec: ProgSnap2Spec) -> str:
    """
    Generate python enum code from a ProgSnap2 link table columns.
    """
    enum_name = f"{link_table_spec.name}Columns"
    enum_values = [id_column for id_column in link_table_spec.id_column_names]
    enum_values += [column.name for column in link_table_spec.additional_columns]
    doc = f"Valid columns for the {link_table_spec.name} LinkTable."
    matching_columns = []
    for id_column in link_table_spec.id_column_names:
        matching_columns.append([col for col in ps2_spec.main_table.columns if col.name == id_column][0])
    docs = [column.description for column in matching_columns]
    docs += [column.description for column in link_table_spec.additional_columns]
    return generate_enum(enum_name, enum_values)