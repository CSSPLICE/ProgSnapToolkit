from analytics.dataset_config import AnalyticsConfig, Granularity
from analytics.preprocessors.codebench import CodeBenchAddParentEventIDs, YAMLLinkURLPreprocessor
from spec.enums import MainTableColumns as Cols, EventType
from dataclasses import replace

_base_name = "codebench"

_base_config = AnalyticsConfig(
    name=_base_name,
    granularity=Granularity.Edit,

    primary_timestamp_column=Cols.ServerTimestamp,
    main_table_preprocessors=[
        CodeBenchAddParentEventIDs(),
    ],
    link_table_preprocessors=[
        YAMLLinkURLPreprocessor(True),
    ],

    compile_error_type_column="ProgramErrorOutput",
    compile_event=EventType.Submit,
    compile_error_event=EventType.RunTest,

    grades_link_table_name="CourseSubject",
    final_grade_column="final-grade",
)

F24 = replace(_base_config,
    name=f"{_base_name}_f24",

    start_time="2024-09-01 00:00:00",
    end_time=None,
)