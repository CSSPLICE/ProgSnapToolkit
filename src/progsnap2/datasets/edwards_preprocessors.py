from progsnap2.analytics.ps2_dataset import Preprocessor
from progsnap2.analytics.ps2_dataset import PS2Dataset
import pandas as pd
from pandas import DataFrame
from progsnap2.spec.enums import MainTableColumns as Cols, EventType
import os

class TimeStampToDateTimePreprocessor(Preprocessor):
    """
    Preprocessor that converts the ClientTimestamp column to datetime.
    """

    def apply(self, dataset: PS2Dataset, main_table: DataFrame) -> DataFrame:
        main_table[Cols.ClientTimestamp] = pd.to_datetime(main_table[Cols.ClientTimestamp], unit='ms', utc=True)
        main_table.sort_values(by=[Cols.ClientTimestamp, Cols.EventID], inplace=True)
        return main_table

class ClassSubsetPreprocessor(Preprocessor):
    """
    Preprocessor that filters the dataset to only include events from the given semester.
    """

    def __init__(self, semester: str):
        """
        :param semester: The semester to filter by, e.g. "Spring" or "Fall".
        """
        self.semester = semester

    def apply(self, dataset: PS2Dataset, main_table: DataFrame) -> DataFrame:
        if self.semester not in ["Spring", "Fall"]:
            raise ValueError(f"Invalid semester: {self.semester}. Must be 'Spring' or 'Fall'.")
        filtered_table = main_table[main_table["X-ClassID"] == self.semester].copy()
        filtered_table[Cols.TermID] = self.semester
        return filtered_table

class AddErrors2021Preprocessor(Preprocessor):
    """
    Preprocessor that adds error messages to the main table.
    Currently not used, and this preprocessing is done and cached.
    """

    def apply(self, dataset: PS2Dataset, main_table: DataFrame) -> DataFrame:
        runs1 = pd.read_csv(os.path.join(dataset.data_config.root_path, 'runs1.csv'))
        runs2 = pd.read_csv(os.path.join(dataset.data_config.root_path, 'runs2.csv'))
        all_runs = pd.concat([runs1, runs2], ignore_index=True)
        runs = self.create_runs_df(all_runs)

        merge_cols = [Cols.SubjectID, Cols.AssignmentID, Cols.ClientTimestamp, Cols.CodeStateSection, Cols.EventType, "X-Metadata"]
        data_cols = [Cols.CompileMessageType, Cols.CompileMessageData]

        main_table = main_table.merge(
            runs[merge_cols + data_cols],
            on=merge_cols,
            how='left',
        )

        main_table[Cols.ParentEventID] = pd.NA
        main_table.loc[main_table.CompileMessageData.notna(), Cols.ParentEventID] = \
            main_table.loc[main_table.CompileMessageData.notna()].EventID

        uncompilable_runs_without_errors_flag = \
            (main_table[Cols.EventType] == EventType.RunProgram) & \
            (main_table["X-Compilable"] == 0) & \
            main_table[Cols.CompileMessageData].isna()

        main_table.loc[uncompilable_runs_without_errors_flag, Cols.CompileMessageType] = "SyntaxError"

        return main_table


    def create_runs_df(self, all_runs: DataFrame) -> DataFrame:
        current_run = None
        rows = []
        stderr = pd.NA

        ignorable_errors = [
            # Not an error: program manually stopped
            'KeyboardInterrupt',
            # Not an error: turtle drawing inturrupted manually
            'turtle.Terminator',
        ]
        no_colon_errors = [
            'random.seed(sum)',
            'numberSpacing = (2 * number) - 1 (- len(numberInRow))',
            'seed(var2)',
        ]

        subset = all_runs[(all_runs.Action == 'r') | (all_runs.OutputDestination == 'stderr')]
        for i, row in subset.iterrows():
            # print(row.Action, row.Action == 'r')
            if row.Action == 'r':
                if current_run is not None:
                    error_type = pd.NA
                    if pd.notna(stderr):
                        last_line = stderr.strip().split('\n')[-1].strip()
                        colon_index = last_line.find(":")
                        if last_line in no_colon_errors:
                            error_type = last_line.strip()
                        elif colon_index != -1:
                            error_type = last_line[:colon_index].strip()
                        else:
                            if last_line not in ignorable_errors:
                                print(f"Unrecognized error type: {last_line}")
                                print(f"Full error message: {stderr}")
                            error_type = pd.NA
                    current_run[Cols.CompileMessageType] = error_type
                    current_run[Cols.CompileMessageData] = stderr
                    rows.append(current_run)
                current_run = row.to_dict()
                stderr = pd.NA
                continue

            if row.OutputDestination == 'stderr':
                output = row.Output.strip()
                if len(output) > 0:
                    if pd.isna(stderr):
                        stderr = ''
                    stderr += output
                    if row.Output.endswith('\n'):
                        stderr += '\n'

        runs = pd.DataFrame(rows)
        runs.rename(columns={
            'File': Cols.CodeStateSection
        }, inplace=True)
        runs[Cols.EventType] = 'Run.Program'
        runs["X-Metadata"] = 'Start'
        return runs
