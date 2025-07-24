import re
import pandas as pd
from analytics.analytics_config import AnalyticsConfig, Granularity

from analytics.ps2_dataset import LinkTablePreprocessor, PS2Dataset, Preprocessor, SortPreprocessor
from database.config import PS2DataConfig
from spec.enums import MainTableColumns as Cols, EventType
from spec.metadata import MetadataValues
from spec.spec_definition import PS2Versions
from dataclasses import replace

class CodeWorkoutExtractErrorTypesPreprocessor(Preprocessor):
    def apply(self, dataset, main_table):
        assert (main_table[Cols.CompileMessageType].isna() == \
            main_table[Cols.CompileMessageData].isna()).all(), (
                "CompileMessageType and CompileMessageData must be both NaN or not NaN."
            )
        main_table[Cols.CompileMessageType] = main_table[Cols.CompileMessageData].apply(
            extract_compile_message_type
        )
        return main_table


def extract_compile_message_type(compile_message: str) -> str:
    if pd.isna(compile_message) or compile_message == "":
        return None
    prefix = r"line [0-9]+: (error: )?"
    compile_message = re.sub(prefix, "", compile_message)
    compile_message = compile_message.strip()
    if compile_message.endswith("."):
        compile_message = compile_message[:-1]
    return compile_message

class RemoveDuplicateGradesPreprocessor(LinkTablePreprocessor):
    def apply(self, dataset, link_table_name, link_table):
        if link_table_name.startswith("Subject"):
            return link_table.drop_duplicates()
        return link_table

def _load_dataset(root_path: str, config: AnalyticsConfig, spec=None):
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


_base_name = "codeworkout"

_base_config = AnalyticsConfig(
    name=_base_name,
    loader=_load_dataset,

    granularity=Granularity.Submission,

    primary_timestamp_column=Cols.ServerTimestamp,
    main_table_preprocessors=[
        SortPreprocessor(Cols.ServerTimestamp),
        CodeWorkoutExtractErrorTypesPreprocessor(),
    ],

    submit_event=EventType.RunProgram,

    final_grade_column="X-Grade",
)

S19 = replace(_base_config,
    name=f"{_base_name}_s19",
    early_time="2019-03-15 00:00:00",

    link_table_preprocessors=[
        # For some reason, the table has one student duplicated
        RemoveDuplicateGradesPreprocessor(),
    ],
)

F19 = replace(_base_config,
    name=f"{_base_name}_f19",
)