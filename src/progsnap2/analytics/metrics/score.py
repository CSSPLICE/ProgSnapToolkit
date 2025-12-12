
from typing import Final
from pandas import DataFrame, Series
from progsnap2.spec.enums import MainTableColumns as Cols, EventType
import numpy as np


class SubmissionScoreMetrics:

    ATTEMPTS: Final[str] = "Attempts"
    """
    The number of attempts made to solve a problem,
    up to and including the first correct attempt.
    Only includes submissions where the student received
    a feedback (i.e., a score).
    """

    FIRST_CORRECT: Final[str] = "FirstCorrect"
    """
    Indicates if the first attempt to solve a problem was correct.
    """

    EVER_CORRECT: Final[str] = "EverCorrect"
    """
    Indicates if there was ever a correct attempt to solve a problem.
    """

    ATTEMPTED: Final[str] = "Attempted"
    """
    Indicates  if there was at least one attempt to solve a problem.
    """

    MAX_SCORE: Final[str] = "MaxScore"
    """
    The maximum score achieved in all attempts made to solve a problem.
    """

    MIN_SCORE: Final[str] = "MinScore"
    """
    The minimum score achieved in all attempts made to solve a problem,
    up to and including the first correct attempt.
    """

    MEAN_SCORE: Final[str] = "MeanScore"
    """
    The mean score of all attempts made to solve a problem
    up to and including the first correct attempt.
    """

    FIRST_SCORE: Final[str] = "FirstScore"
    """
    The score of the first attempt made to solve a problem.
    """

    TOTAL_ATTEMPTS: Final[str] = "TotalAttempts"
    """
    The total number of attempts made to solve a problem,
    including all attempts, even after the first correct attempt.
    """



    def __init__(self, submit_event: str = EventType.Submit.value, correctness_threshold: float = 1.0):
        self.submit_event = submit_event
        self.correctness_threshold = correctness_threshold

    def calculate(self, rows: DataFrame) -> dict[str, any]:

        rows = rows[rows[Cols.EventType] == self.submit_event]
        scores = rows[Cols.Score]

        max_score = scores.max() if not scores.empty else 0
        total_attempts = len(scores)

        scores_until_correct = scores

        correct_indices = np.array([])
        if Cols.Score in rows.columns:
            is_correct = (rows[Cols.Score] >= self.correctness_threshold).to_numpy()
            correct_indices = np.where(is_correct)[0]

        ever_correct = correct_indices.size > 0

        if ever_correct:
            first_correct_loc = correct_indices[0]
             # Offset by 1 to include the first correct attempt
            after_correct_loc = first_correct_loc + 1
            scores_until_correct = scores.iloc[:after_correct_loc]

        attempts = scores_until_correct.notna().sum()
        first_correct = not scores_until_correct.empty and \
            scores_until_correct.iloc[0] >= self.correctness_threshold
        first_score = scores_until_correct.iloc[0] if not scores_until_correct.empty else 0
        attempted = attempts > 0
        min_score = scores_until_correct.min() if not scores_until_correct.empty else 0
        mean_score = scores_until_correct.mean() if not scores_until_correct.empty else 0


        score_metrics = {
            self.ATTEMPTS: attempts,
            self.FIRST_CORRECT: first_correct,
            self.EVER_CORRECT: ever_correct,
            self.ATTEMPTED: attempted,
            self.MAX_SCORE: max_score,
            self.MIN_SCORE: min_score,
            self.MEAN_SCORE: mean_score,
            self.FIRST_SCORE: first_score,
            self.TOTAL_ATTEMPTS: total_attempts
        }
        return Series(score_metrics)

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
