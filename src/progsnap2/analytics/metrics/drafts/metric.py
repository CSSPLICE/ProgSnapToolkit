from abc import ABC, abstractmethod
from typing import Callable, Optional
from pandas import DataFrame
from pandas.api.typing import DataFrameGroupBy


class Metric(ABC):
    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self.enabled = True

    @abstractmethod
    def calculate(self, df: DataFrame) -> any:
        """
        Apply the metric to the DataFrame and return the result.
        """
        pass

    def __str__(self):
        return self.name

class LambdaMetric(Metric):
    def __init__(self, name: str, function: Callable[[DataFrame], any]):
        super().__init__(name)
        self.function = function

    def calculate(self, df: DataFrame) -> any:
        return self.function(df)


class MetricCalculator:
    def __init__(self, grouping_cols: list[str], metrics: list[Metric]):
        self.grouping_cols = grouping_cols
        self.metrics = metrics

    def apply_to_group(self, group: DataFrame) -> dict[str, any]:
        """
        Apply the metrics to a single group and return a dictionary of results.
        """
        result = {}
        for metric in self.metrics:
            metric_result = metric.calculate(group)
            if isinstance(metric_result, dict):
                for key, value in metric_result.items():
                    result[key] = value
            else:
                result[metric.name] = metric_result
        return result

    def apply(self, df: DataFrame) -> DataFrame:
        """
        Apply the metrics to the DataFrame and return a new DataFrame with the results.
        """
        grouped = df.groupby(self.grouping_cols)
        return grouped.apply(lambda x: self.apply_to_group(x))