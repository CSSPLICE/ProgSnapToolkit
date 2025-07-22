from analytics.dataset_config import AnalyticsConfig, Granularity
from analytics.preprocessors.codebench import CodeBenchAddParentEventIDs, YAMLLinkURLPreprocessor
from analytics.preprocessors.codeworkout import CodeWorkoutExtractErrorTypesPreprocessor
from analytics.ps2_dataset import PS2Dataset, SortPreprocessor
from database.config import PS2DataConfig
from spec.enums import MainTableColumns as Cols, EventType
from spec.metadata import MetadataValues
from spec.spec_definition import PS2Versions
from dataclasses import replace

_base_name = "codeworkout"

_base_config = AnalyticsConfig(
    name=_base_name,
    granularity=Granularity.Submission,

    primary_timestamp_column=Cols.ServerTimestamp,
    main_table_preprocessors=[
        # TODO: It's already sorted by Order, but Timestamps aren't in order...
        # SortPreprocessor(),
        CodeWorkoutExtractErrorTypesPreprocessor(),
    ],

    submit_event=EventType.RunProgram,

    final_grade_column="X-Grade",
)

def load_dataset(root_path: str, config: AnalyticsConfig, spec=None):
    spec = PS2Versions.v1_0.load() if spec is None else spec
    data_config = PS2DataConfig(
        root_path=root_path,
        main_table_file="MainTable.csv",
        metadata_file="Metadata.csv",
        codestates_table_relative_path="LinkTables/CodeStates.csv",
        # CWO Doesn't provide metadata, so we create one that mostly
        # uses defaults
        metadata=MetadataValues(
            IsEventOrderingConsistent=True
        )
    )
    dataset = PS2Dataset(spec, data_config)
    for i, step in enumerate(config.main_table_preprocessors):
        dataset.main_table_preprocessors.insert(i, step)
    for i, step in enumerate(config.link_table_preprocessors):
        dataset.link_table_preprocessors.insert(i, step)
    return dataset

# TODO: There's an issue where 2 students took the class in
# 2 different sections, but the grades table only has them once...
# Looks like it's students who transferred sections, so I really just
# shouldn't group by that column
S19 = replace(_base_config,
    name=f"{_base_name}_s19",
    early_time="2019-03-15 00:00:00",
)

F19 = replace(_base_config,
    name=f"{_base_name}_f19",
)