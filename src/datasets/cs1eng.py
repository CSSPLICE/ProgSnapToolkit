from analytics.analytics_config import AnalyticsConfig, Granularity
from spec.enums import MainTableColumns as Cols, EventType
from dataclasses import replace

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
    name=f"{_base_name}_s24",
    # early_time="2019-03-15 00:00:00", TODO
)