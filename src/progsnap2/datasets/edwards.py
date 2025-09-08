from progsnap2.analytics.analytics_config import AnalyticsConfig, Granularity, ProgrammingLanguage
from progsnap2.datasets.edwards_preprocessors import ClassSubsetPreprocessor, TimeStampToDateTimePreprocessor
from progsnap2.database.config import PS2DataConfig
from progsnap2.spec.enums import MainTableColumns as Cols, EventType
from dataclasses import replace

from progsnap2.spec.metadata import MetadataValues

def _create_data_config(root_path: str):
    return PS2DataConfig(
        root_path=root_path,
        main_table_file="MainTable.csv",
        # These datasets don't provide metadata, so we create one that mostly
        # using defaults
        metadata=MetadataValues(
            IsEventOrderingConsistent=True,
            EventOrderScope="Global",
        )
    )

_base_name = "edwards"

_base_2019_config = AnalyticsConfig(
    name=_base_name,
    create_data_config=_create_data_config,
    programming_language=ProgrammingLanguage.Python,
    granularity=Granularity.Keystroke,

    primary_timestamp_column=Cols.ClientTimestamp,
    main_table_preprocessors=[
        TimeStampToDateTimePreprocessor(),
    ],

    compile_event=EventType.RunProgram,

    grades_link_table_name="SubjectTerm",
    final_grade_column="exam2",
)
_base_2019_config.attempt_grouping_columns.append(Cols.TermID)

S19 = replace(_base_2019_config,
    name=f"{_base_name}_s19",

    start_time=None,
    end_time="2019-02-25 00:00:00",
    early_time='2019-02-04 00:00:00',
)
# Copy the list before modification, since replace is a shallow copy!
S19.main_table_preprocessors = S19.main_table_preprocessors.copy()
S19.main_table_preprocessors.append(
    ClassSubsetPreprocessor("Spring")
)

F19 = replace(_base_2019_config,
    name=f"{_base_name}_f19",

    start_time=None,
    end_time="2019-10-13 00:00:00",
    early_time='2019-09-22 00:00:00',
)
F19.main_table_preprocessors = F19.main_table_preprocessors.copy()
F19.main_table_preprocessors.append(
    ClassSubsetPreprocessor("Fall")
)

F21 = replace(_base_2019_config,

    name=f"{_base_name}_f21",
    end_time="2021-12-15 00:00:00",
    early_time='2021-10-24 00:00:00',

    start_time=None,
    primary_problem_grouping_column=Cols.AssignmentID,
    final_grade_column="FinalScore",
    grades_link_table_name="Subject",
)
