from analytics.analytics_config import AnalyticsConfig, Granularity
from database.config import PS2DataConfig
from spec.enums import MainTableColumns as Cols, EventType
from dataclasses import replace

def _create_data_config(root_path: str, name: str):
    return PS2DataConfig(
        root_path=root_path,
        sqlalchemy_url=f"sqlite:///{root_path}/{name}.sqlite3",
    )

_base_name = "cs1eng"

_base_config = AnalyticsConfig(
    name=_base_name,
    granularity=Granularity.Edit,

    primary_timestamp_column=Cols.ServerTimestamp,
    main_table_preprocessors=[
    ],

    submit_event=EventType.Submit,

    final_grade_column="X-Grade", # TODO
)

S24 = replace(_base_config,
    name=f"{_base_name}_S24",
    create_data_config=lambda root_path: _create_data_config(root_path, "S24"),

    # early_time="2019-03-15 00:00:00", TODO
)