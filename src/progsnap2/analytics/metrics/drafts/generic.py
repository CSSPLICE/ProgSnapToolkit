
from pandas import DataFrame
from analytics.metrics.drafts.metric import Metric
from spec.enums import MainTableColumns as Cols

CORRECT_SCORE = 1

class LogCount(Metric):
    """
    A metric that counts the number of logs.
    """

    def calculate(self, logs: DataFrame) -> int:
        return len(logs)

class NumberOfIncorrectAttempts(Metric):
    """
    A metric that counts the number of incorrect attempts.
    """

    def calculate(self, logs: DataFrame) -> int:
        return (logs[Cols.Score] < CORRECT_SCORE).sum()

class NumberOfCorrectAttempts(Metric):
    """
    A metric that counts the number of correct attempts.
    """

    def calculate(self, logs: DataFrame) -> int:
        return (logs[Cols.Score] >= CORRECT_SCORE).sum()

class MeanScore(Metric):
    """
    A metric that calculates the mean score.
    """

    def calculate(self, logs: DataFrame) -> float:
        return logs[Cols.Score].mean()

class MaxScore(Metric):
    """
    A metric that calculates the maximum score.
    """

    def calculate(self, logs: DataFrame) -> float:
        return logs[Cols.Score].max()

class EverCorrect(Metric):
    """
    A metric that checks if there was ever a correct attempt.
    """

    def calculate(self, logs: DataFrame) -> bool:
        return (logs[Cols.Score] >= CORRECT_SCORE).any()