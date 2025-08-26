from jinja2 import Template

from spec.spec_definition import ProgSnap2Spec, Column
from spec.datatypes import PS2Datatype
import textwrap

def create_ts_template():
    return """
/**
 * Logs a "{{ event_name }}" event to the server.
 * {{ docstring }}
 *
{% for arg in args %} * @param {{ arg.name }} - {{ arg.ps2_name }}: {{ arg.description }}
{% endfor %} * @returns void
 */
public {{ method_name }}({% for arg in args %}{{ arg.name }}{{ arg.optional_q  }}: {{ arg.type }}{% if not loop.last %}, {% endif %}{% endfor %}) {
    this.logEvent(EventType.{{ event_type }}, {
        {% for arg in args %}{{ arg.ps2_name }}: {{ arg.name }}{% if not loop.last %}, {% endif %}{% endfor %}
    });
}
"""

def map_to_ts_type(column: Column) -> str:
    if column.datatype == PS2Datatype.Enum:
        return "PS2." + column.name # + "Type"
    return column.datatype.typescript_type

def camel_case(s: str):
    parts = s.split(".")
    return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])

def pascal_case(s: str):
    parts = s.split(".")
    return ''.join(p.capitalize() for p in parts)

def format_arg_description(description: str) -> str:
    if not description:
        return ""
    lines = description.split("\n")
    lines = [line.strip() for line in lines if line.strip()]
    return "\n * ".join(lines)

def add_args(columns: list[str], is_required: bool, spec: ProgSnap2Spec, args: list):
    if columns is None:
        return
    for col_name in columns:
        col = spec.main_table.get_column(col_name)
        if col:
            ts_type = map_to_ts_type(col)
            ps2_name = col.name
            name = ps2_name[0].lower() + ps2_name[1:]
            args.append({
                "name": name,
                "type": ts_type,
                "ps2_name": ps2_name,
                "optional_q": "?" if not is_required else "",
                "description": format_arg_description(col.description),
            })
        else:
            raise ValueError(f"Column {col_name} not found in schema.")

def generate_ts_methods(schema: ProgSnap2Spec) -> str:
    template = Template(create_ts_template())
    methods = []
    for evt in schema.main_table.event_types:
        args = []
        add_args(evt.required_columns, True, schema, args)
        add_args(evt.optional_columns, False, schema, args)

        method_str = template.render(
            method_name="log" + pascal_case(evt.name),
            event_name=evt.name,
            event_type=evt.name.upper().replace(".", "_"),
            args=args,
            docstring=evt.description if evt.description else "",
        )
        methods.append(textwrap.indent(method_str, "    "))
    return "\n\n".join(methods)
