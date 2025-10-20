import pandas as pd
from pandas import DataFrame
from progsnap2.database.codestate.codestate_writer import CodeStateWriter
from progsnap2.spec.codestate import CodeStateEntry
from progsnap2.spec.enums import MainTableColumns as Cols, CodeStatesTableColumns as CodeCols, EventType


class KeystrokeCodestateIO(CodeStateWriter):

    # TODO: These aren't reasonable default grouping columns; need a way to configure
    # I'm tempted to just say it's ProjectID always and add that to Edwards
    def __init__(self, grouping_cols = [Cols.SubjectID, Cols.AssignmentID], order_col = None):
        super().__init__()
        self.grouping_cols = grouping_cols
        self.order_col = order_col

    def add_codestate_and_get_id(self, codestate: CodeStateEntry) -> str:
        raise NotImplementedError("KeystrokeCodestateIO is currently read only.")

    def add_codestate_with_id(self, codestate: CodeStateEntry, codestate_id: str) -> str:
        raise NotImplementedError("KeystrokeCodestateIO is currently read only.")

    def get_codestates_table(self) -> DataFrame:
        raise NotImplementedError("""
            In the Keystroke CodeStates format, loading all codestates is very time consuming.
            For best results, load only a subset of codestates using get_codestates_table_subset(codestate_ids).
            If you need all codestates, you can pass a list of all codestate IDs to that function.""")

    def do_codestates_have_sections(self) -> bool:
        return True

    @staticmethod
    def reconstruct_all(df, in_place=False):
        if not in_place:
            df = df.copy()
        codestates = []
        s = ''
        for _, row in df.iterrows():
            if row[Cols.EventType] == EventType.FileEdit:
                i = int(row[Cols.SourceLocation])
                insert = '' if pd.isna(row.InsertText) else row.InsertText
                delete = '' if pd.isna(row.DeleteText) else row.DeleteText
                if i > len(s):
                    raise ValueError(f"SourceLocation {i} is out of bounds for current code length {len(s)}. \
                                     Are you sure you are passing a contiguous edit sequence?")
                s = s[:i] + insert + s[i+len(delete):]
            codestates.append(s)
        df[CodeCols.Code] = codestates
        return df

    def get_codestates_table_subset(self, rows: DataFrame) -> DataFrame:
        required_cols = list(self.grouping_cols) + [Cols.EventType, Cols.SourceLocation, 'InsertText', 'DeleteText']
        if self.order_col is not None:
            required_cols.append(self.order_col)
        self._check_dataframe_for_codestate_columns(rows, required_cols)

        parts = []
        for _, group in rows.groupby(required_cols, as_index=False):
            if self.order_col is not None:
                # Confirm the group is in contiguous order
                if not group[self.order_col].is_monotonic_increasing:
                    raise ValueError(f"Rows for project/grouping id {group.iloc[0][self.grouping_cols]} are not in order by {self.order_col}.")
            part = KeystrokeCodestateIO.reconstruct_all(group)
            parts.append(part)

        return pd.concat(parts, ignore_index=True)

