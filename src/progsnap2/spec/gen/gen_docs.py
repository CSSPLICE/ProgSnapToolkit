

from typing import List

from spec.datatypes import PS2Datatype
from spec.enums import MainTableColumns
from spec.spec_definition import Column, EnumValue, MainTable, MetadataProperty, ProgSnap2Spec, Property, Requirement

def make_markdown_table(headers, rows):
    # Combine headers and rows to compute the maximum width of each column
    columns = list(zip(*([headers] + rows)))
    col_widths = [max(len(str(cell)) for cell in col) for col in columns]

    # Helper to format a row
    def format_row(row):
        return "| " + " | ".join(str(cell).ljust(width) for cell, width in zip(row, col_widths)) + " |"

    # Build the table
    table = [format_row(headers)]
    separator = "| " + " | ".join("-" * width for width in col_widths) + " |"
    table.append(separator)
    for row in rows:
        table.append(format_row(row))

    return "\n".join(table)

def get_enum_table(enum_values: List[EnumValue], add_links=False) -> str:
    headers = ["Enum Value", "Description"]
    rows = []
    for enum_value in enum_values:
        description = enum_value.description or ""
        name = enum_value.name
        if add_links:
            name = f"<a id='{format_event_type_link(name)}'></a>{name}"
        rows.append([name, description])
    return headers, rows

def format_enum_table_rows(enum_values: List[EnumValue]) -> str:
    headers, rows = get_enum_table(enum_values)
    return make_markdown_table(headers, rows)

def format_event_type_enum_table(spec: ProgSnap2Spec) -> str:
    headers, rows = get_enum_table(spec.main_table.event_types, True)
    headers += ["Required Columns", "Optional Columns"]
    for i, _ in enumerate(rows):
        event_type = spec.main_table.event_types[i]
        required_columns = format_event_type_linked_column(event_type.required_columns, spec)
        optional_columns = format_event_type_linked_column(event_type.optional_columns, spec)
        rows[i] += [required_columns, optional_columns]
    return make_markdown_table(headers, rows)

def format_event_type_linked_column(columns: list[str], spec: ProgSnap2Spec) -> str:
    """
    Format the linked columns for an event type.
    """
    if columns is None:
        return ""
    parts = []
    for col_name in columns:
        col = spec.main_table.get_column(col_name)
        parts.append(f"[{col.name}](#{col.name.lower()})")
    return ", ".join(parts)

# TODO: Something's wrong with the MD formatting if this includes bullets (may be in the yaml...)
# --- Shared Helper to Render Description ---
def render_description(description: str) -> str:
    return f"\n{description.strip()}" if description else ""

def format_event_type_link(type: str) -> str:
    return type.replace(".", "").lower()

# --- Shared Renderer for Property, Column, and MetadataProperty ---
def render_property(prop: Property, spec: ProgSnap2Spec) -> str:
    lines = [f"### {prop.name}"]

    if isinstance(prop, Column):
        lines.append(f"- *Requirement Type*: {prop.requirement.value}")

    lines.append(f"- *Datatype*: {prop.datatype.name}")

    if isinstance(prop, MetadataProperty):
        lines.append(f"- *Default value*: {prop.default_value if prop.default_value is not None else 'None'}")

    if isinstance(prop, Column):
        if prop.requirement == Requirement.EventSpecific:
            required_events = [event for event in spec.main_table.event_types if event.is_column_required(prop.name)]
            if required_events:
                lines.append("- *Required for*:")
                for event in required_events:
                    lines.append(f"    - [{event.name}](#{format_event_type_link(event.name)})")
            optional_events = [event for event in spec.main_table.event_types if event.is_column_optional(prop.name)]
            if optional_events:
                lines.append("- *Optional for*:")
                for event in optional_events:
                    lines.append(f"    - [{event.name}](#{format_event_type_link(event.name)})")

    if prop.datatype == PS2Datatype.Enum:
        lines.append(f"\n**{prop.name} Allowed Values**:\n")
        if prop.name == MainTableColumns.EventType:
            lines.append(format_event_type_enum_table(spec))
        else:
            enum_type = next((et for et in spec.enum_types if et.name == prop.name), None)
            if enum_type:
                lines.append(format_enum_table_rows(enum_type.values))
            else:
                raise ValueError(f"Enum type {prop.name} not found in spec.")


    lines.append(render_description(prop.description))
    return "\n".join(lines)

def render_metadata_section(spec: ProgSnap2Spec) -> str:
    lines = ["# Metadata Table"]
    lines.append(render_description(spec.metadata.description))
    for prop in spec.metadata.properties:
        lines.append(render_property(prop, spec))
    return "\n\n".join(lines)

def render_main_table_columns_group(columns: List[Column], category: Requirement, spec: ProgSnap2Spec) -> str:
    if category == Requirement.EventSpecific:
        name = "Event-specific Columns"
    elif category == Requirement.Required:
        name = "Universal Required Columns"
    else:
        name = "Universal Optional Columns"

    lines = [f"## {name}"]

    for col in columns:
        lines.append(render_property(col, spec))
    return "\n\n".join(lines)

def render_main_table_columns(spec: ProgSnap2Spec) -> str:
    lines = []

    for category in Requirement:
        columns_subset = [col for col in spec.main_table.columns if col.requirement == category]
        lines.append(render_main_table_columns_group(columns_subset, category, spec))

    return "\n\n".join(lines)

def render_main_table(spec: ProgSnap2Spec) -> str:
    lines = ["# Main Table"]
    lines.append(render_description(spec.main_table.description))
    lines.append(render_main_table_columns(spec))
    return "\n\n".join(lines)

def render_link_tables(spec: ProgSnap2Spec) -> str:
    lines = ["# Link Tables"]
    for link_table in spec.link_tables:
        table_lines = []
        table_lines.append(f"## {link_table.name}")
        table_lines.append(render_description(link_table.description))

        if link_table.id_column_names:
            table_lines.append("\n*Required ID Columns*:\n")
            for col in link_table.id_column_names:
                table_lines.append(f"- [{col}](#{col.lower()})")
            table_lines.append("\n")

        if link_table.additional_columns:
            table_lines.append("\n*Additional Columns*:\n")
            for col in link_table.additional_columns:
                table_lines.append(render_property(col, spec))
                table_lines.append("\n")
        lines.append("\n".join(table_lines))
    return "\n\n".join(lines)

def render_spec(spec: ProgSnap2Spec) -> str:
    """
    Render the entire specification as a Markdown document.
    """
    lines = []
    lines.append(f"# ProgSnap2 v{spec.version}")
    lines.append("""\nThis document describes details of the ProgSnap2 specification. A full reference on the specification can be found [here](https://docs.google.com/document/d/1qknzmWr1FL3r8a2BoYyIBQDSWEgBs1jhzdrR-bYh4zI/edit?tab=t.0).""")
    lines.append(render_metadata_section(spec))
    lines.append(render_main_table(spec))
    lines.append(render_link_tables(spec))
    return "\n\n".join(lines)