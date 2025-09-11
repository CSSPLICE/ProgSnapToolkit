from progsnap2.analytics.analytics_config import AnalyticsConfig, Granularity, ProgrammingLanguage
from progsnap2.analytics.ps2_dataset import SortPreprocessor
from progsnap2.database.config import PS2DataConfig
from progsnap2.spec.enums import MainTableColumns as Cols, EventType
from dataclasses import replace

def _create_data_config(root_path: str):
    return PS2DataConfig(
        root_path=root_path,
        # TODO: Maybe rename to DatasetMetadata and .sqlite3 for consistency when releasing?
        metadata_table_name="Metadata",
        sqlalchemy_url=f"sqlite:///{root_path}/falconcode.sqlite",
    )

_base_name = "falconcode"

_base_config = AnalyticsConfig(
    name=_base_name,
    programming_language=ProgrammingLanguage.Python,
    granularity=Granularity.Submission,

    primary_timestamp_column=Cols.ServerTimestamp,
    main_table_preprocessors=[
        SortPreprocessor(),
    ],

    final_grade_column=None,
)

S21 = replace(_base_config,
    name=f"{_base_name}_s21",
    create_data_config=_create_data_config,
    early_time=None, # TODO
)

F21 = replace(_base_config,
    name=f"{_base_name}_f21",
    create_data_config=_create_data_config,
    early_time=None, # TODO
)

S22 = replace(_base_config,
    name=f"{_base_name}_s22",
    create_data_config=_create_data_config,
    early_time=None, # TODO
)