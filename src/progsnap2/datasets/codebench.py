from progsnap2.analytics.analytics_config import AnalyticsConfig, Granularity, ProgrammingLanguage
from progsnap2.analytics.preprocessors.codebench import CodeBenchAddParentEventIDs, CodeBenchRemoveGradeDuplicatesPreprocessor, CodeBenchRemoveSmallClassesPreprocessor, YAMLLinkURLPreprocessor
from progsnap2.database.config import PS2DataConfig
from progsnap2.spec.enums import MainTableColumns as Cols, EventType
from dataclasses import replace

def _create_data_config(root_path: str):
    return PS2DataConfig(
        root_path=root_path,
        main_table_file="MainTable.csv",
        metadata_table_name="DatasetMetadata.csv",
    )

_base_name = "codebench"

_base_config = AnalyticsConfig(
    name=_base_name,
    create_data_config=_create_data_config,
    granularity=Granularity.Keystroke,

    primary_timestamp_column=Cols.ServerTimestamp,
    main_table_preprocessors=[
        CodeBenchAddParentEventIDs(),
        CodeBenchRemoveSmallClassesPreprocessor(min_count=1000),
    ],
    link_table_preprocessors=[
        YAMLLinkURLPreprocessor(True),
        CodeBenchRemoveGradeDuplicatesPreprocessor(),
    ],

    compile_error_type_column="ProgramErrorOutput",
    compile_event=EventType.Submit,
    compile_error_event=EventType.RunTest,

    grades_link_table_name="CourseCourseSectionSubject",
    attempt_grouping_columns=[Cols.SubjectID, Cols.AssignmentID, Cols.ProblemID, Cols.CourseSectionID],
    final_grade_column="final-grade",
    programming_language=ProgrammingLanguage.Python,
)

# TODO: Seems like some logs are just one-off X-File.Blur events, so we
# may want some sort of preprocessing to filter only real attempts

_base_config.attempt_grouping_columns += [
    Cols.CourseID,
    # Seems like students only get one grade per course,
    # so we don't need to group by CourseSectionID for prediction purposes.
    # Cols.CourseSectionID,
]

F24 = replace(_base_config,
    name=f"{_base_name}_f24",

    start_time="2024-09-01 00:00:00",
    end_time=None,
    early_time="2024-09-28 00:00:00",
)