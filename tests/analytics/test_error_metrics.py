from dataclasses import dataclass
from itertools import pairwise
from analytics.metrics.errors import ErrorMetrics

@dataclass
class ErrorTestData:
    name: str
    errors_list: list[str]
    eq: float
    red: float

    def pairwise(self):
        return list(pairwise(
            map(lambda x: [x] if x is not None else [], self.errors_list)
        ))

test_data = [
    ErrorTestData("1", [
        "x", None
    ], 0.0, 0.0),

    ErrorTestData("1 spaced", [
        "x", None, "x",
    ], 0.0, 0.0),

    ErrorTestData("1 interleaved", [
        "x", "y", "x",
    ], 8/11, 0.0),

    ErrorTestData("1 repeated", [
        "x", "x",
    ], 1, 0.5),

    ErrorTestData("2x2 repeated spaced", [
        "x", "x", None, "x", "x"
    ], 0.5, 1),

    ErrorTestData("3 repeated", [
        "x", "x", "x"
    ], 1, 4/3),

    ErrorTestData("2x3 repeated spaced", [
        "x", "x", None, "x", "x", None, "x", "x"
    ], 3/7, 1.5),

    ErrorTestData("3, 2 repeated spaced", [
        "x", "x", "x", None, "x", "x"
    ], 3/5, 33/18),
]


def test_RED_scorer():

    em = ErrorMetrics(True)

    for data in test_data:
        pairwise_errors = data.pairwise()
        red = em._red_scorer(pairwise_errors)
        assert red == data.red, f"Expected RED score {data.red} for {data.name}, got {red}"

def test_EQ_scorer():

    em = ErrorMetrics(True)

    for data in test_data:
        pairwise_errors = data.pairwise()
        eq = em._eq_scorer(pairwise_errors)
        assert eq == data.eq, f"Expected EQ score {data.eq} for {data.name}, got {eq}"