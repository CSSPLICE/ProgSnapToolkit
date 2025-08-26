from progsnap2.analytics.analytics_config import AnalyticsConfig, Granularity
from progsnap2.analytics.preprocessors.edwards import ClassSubsetPreprocessor, TimeStampToDateTimePreprocessor
from progsnap2.spec.enums import MainTableColumns as Cols, EventType
from dataclasses import replace

_base_name = "edwards"

_base_2019_config = AnalyticsConfig(
    name=_base_name,
    granularity=Granularity.Keystroke,

    primary_timestamp_column=Cols.ClientTimestamp,
    main_table_preprocessors=[
        # Don't need this, since I've done and cached it
        # AddErrors2021Preprocessor(),
        TimeStampToDateTimePreprocessor(),
    ],

    compile_event=EventType.RunProgram,

    grades_link_table_name="CourseSubject",
    final_grade_column="exam2",
)

S19 = replace(_base_2019_config,
    name=f"{_base_name}_s19",

    start_time=None,
    end_time="2019-02-25 00:00:00",
    early_time=None, # TODO
)
S19.main_table_preprocessors.append(
    ClassSubsetPreprocessor("Spring")
)

F19 = replace(_base_2019_config,
    name=f"{_base_name}_f19",

    start_time=None,
    end_time="2019-10-13 00:00:00",
    early_time=None, # TODO
)
F19.main_table_preprocessors.append(
    ClassSubsetPreprocessor("Fall")
)

# TODO: Need to figure out what to do with the "Group" column in the grades link table