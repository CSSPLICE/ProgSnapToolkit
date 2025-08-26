
from typing import Final
from pandas import DataFrame, Series
from progsnap2.analytics.ps2_dataset import PS2Dataset
from progsnap2.spec.enums import MainTableColumns as Cols
import numpy as np


class TimeMetrics:

    ACTIVE_TIME: Final[str] = "ActiveTime"
    """
    The time spent actively working on a problem, ignoring idle time and breaks,
    as well as time after the first correct attempt.
    """
    PASSIVE_TIME: Final[str] = "PassiveTime"
    """
    The time spent idle, not actively working on a problem. Does not inclide breaks,
    as well as time after the first correct attempt.
    Idle time is defined as a gap of time longer than the idle_gap, but shorter than
    the break_gap.
    """
    TOTAL_TIME: Final[str] = "TotalTime"
    """
    The total time spent on a problem, including idle time, but ignoring long breaks, until
    the first correct attempt.
    """
    ACTIVE_TIME_AFTER_CORRECT: Final[str] = "ActiveTimeAfterCorrect"
    """
    The time spent actively working on a problem after the first correct attempt.
    """
    N_BREAKS: Final[str] = "#Breaks"
    """
    The number of breaks taken while working on a problem. A break is a gap of time
    longer than the break_gap.
    """

    START_TIME: Final[str] = "StartTime"
    """
    The time of the first log entry for a problem.
    """
    FIRST_CORRECT_TIME: Final[str] = "FirstCorrectTime"
    """
    The time of the first correct attempt for a problem.
    """

    END_TIME: Final[str] = "EndTime"
    """
    The time of the last log entry for a problem.
    It is often more useful to use FIRST_CORRECT_TIME.
    """


    def __init__(self, idle_gap, break_gap, is_data_already_time_sorted, time_col: str = Cols.ClientTimestamp):
        self.idle_gap = idle_gap
        self.break_gap = break_gap
        self.time_col = time_col
        self.sort_first = not is_data_already_time_sorted


    def calculate(self, rows: DataFrame) -> dict[str, any]:
        if self.sort_first:
            rows = rows.sort_values(by=[self.time_col])


        time_series = rows[self.time_col]

        start_time = time_series.iloc[0]

        time_series_until_correct = time_series
        time_series_after_correct = None

        correct_indices = np.array([])
        if Cols.Score in rows.columns:
            is_correct = (rows[Cols.Score] >= 1).to_numpy()
            correct_indices = np.where(is_correct)[0]

        first_correct_time = None
        if correct_indices.size > 0:
            first_correct_loc = correct_indices[0]
            first_correct_time = time_series.iloc[first_correct_loc]
             # Offset by 1 to include the first correct attempt
            after_correct_loc = first_correct_loc + 1
            time_series_until_correct = time_series.iloc[:after_correct_loc]
            time_series_after_correct = time_series.iloc[after_correct_loc:]

        delta_seconds = time_series_until_correct.diff().dt.total_seconds()
        negative_deltas = delta_seconds < 0
        if negative_deltas.any():
            print("Warning: Negative time deltas found. This may indicate incorrect timestamps or data sorting issues.")
            delta_seconds = delta_seconds[~negative_deltas]  # Remove negative deltas
        n_breaks = (delta_seconds > self.break_gap).sum()
        non_break_seconds = delta_seconds[delta_seconds <= self.break_gap]
        passive_time = non_break_seconds[non_break_seconds > self.idle_gap].sum()
        total_time = non_break_seconds.sum()
        active_time = total_time - passive_time

        active_time_after_correct = 0
        if time_series_after_correct is not None:
            delta_seconds_after_correct = time_series_after_correct.diff().dt.total_seconds()
            non_break_seconds_after_correct = delta_seconds_after_correct[delta_seconds_after_correct <= self.break_gap]
            active_time_after_correct = non_break_seconds_after_correct[non_break_seconds_after_correct <= self.idle_gap].sum()

        time_metrics = {
            self.ACTIVE_TIME: active_time,
            self.PASSIVE_TIME: passive_time,
            self.TOTAL_TIME: total_time,
            self.ACTIVE_TIME_AFTER_CORRECT: active_time_after_correct,
            self.N_BREAKS: n_breaks,
            self.START_TIME: start_time,
            self.FIRST_CORRECT_TIME: first_correct_time,
            self.END_TIME: time_series.iloc[-1],
        }
        return Series(time_metrics)

    @staticmethod
    def get_all_diffs(ungrouped_rows: DataFrame, time_col: str, grouping_cols: list[str]) -> DataFrame:
        """
        Get all time differences for the given rows in seconds.
        Differences are calculated within each group defined by the grouping columns,
        e.g. within one SubjectID working on one ProblemID.
        These values should be used to set the idle_gap and break_gap
        parameters for the TimeMetrics class.
        """
        df = ungrouped_rows.sort_values(by=grouping_cols + [time_col])[grouping_cols]
        df["DeltaSeconds"] = ungrouped_rows.groupby(grouping_cols)[time_col].diff().apply(lambda x: x.total_seconds())

        return df

    @staticmethod
    def get_positive_diff_quantiles(ungrouped_rows: DataFrame, time_col: str, grouping_cols: list[str]):
        """
        Get the quantiles of positive time differences for the given rows in seconds.
        See get_all_diffs for more details.
        """
        df = TimeMetrics.get_all_diffs(ungrouped_rows, time_col, grouping_cols)
        df = df[df["DeltaSeconds"] > 0]  # Filter out non-positive deltas
        quantiles = np.array([0, 25, 50, 75, 80, 85, 90, 95, 96, 97, 98, 99, 100])
        return df["DeltaSeconds"].quantile(quantiles / 100)

    def test_calculation(self, ungrouped_rows: DataFrame, grouping_cols: list[str], n = 5) -> Series:
        """
        Test the calculation on the first n groups based on the grouping columns.
        This is useful for debugging and verifying the calculation logic.
        """

        if not grouping_cols:
            raise ValueError("Grouping columns must be provided for testing.")

        grouped = ungrouped_rows.groupby(grouping_cols)

        results = []

        cols = None
        # Iterate and apply function only to the first `n` groups
        for i, (name, group) in enumerate(grouped):
            if i >= n:
                break
            # Apply your function here (e.g., sum of 'value')
            result = self.calculate(group)
            cols = result.index if cols is None else cols
            result = result.to_dict()
            result['Group'] = name
            results.append(result)

        # Convert to DataFrame or Series if needed
        result_df = DataFrame(results)
        return result_df
