import re
import pandas as pd
from analytics.ps2_dataset import Preprocessor
from spec.enums import MainTableColumns as Cols, EventType


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