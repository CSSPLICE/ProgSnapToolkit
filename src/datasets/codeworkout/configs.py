from analytics.dataset_config import AnalyticsConfig, Granularity
from analytics.preprocessors.codebench import CodeBenchAddParentEventIDs, YAMLLinkURLPreprocessor
from analytics.preprocessors.codeworkout import CodeWorkoutExtractErrorTypesPreprocessor
from analytics.ps2_dataset import SortPreprocessor
from spec.enums import MainTableColumns as Cols, EventType
from dataclasses import replace

_base_name = "codeworkout"

_base_config = AnalyticsConfig(
    name=_base_name,
    granularity=Granularity.Submission,

    primary_timestamp_column=Cols.ServerTimestamp,
    main_table_preprocessors=[
        SortPreprocessor(),
        CodeWorkoutExtractErrorTypesPreprocessor(),
    ],

    submit_event=EventType.RunProgram,

    final_grade_column="X-Grade",
)

S19 = replace(_base_config,
    name=f"{_base_name}_s19",
    early_time="2019-03-15 00:00:00",
)

F19 = replace(_base_config,
    name=f"{_base_name}_f19",
)