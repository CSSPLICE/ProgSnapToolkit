
from typing import Final, List, Set, Tuple
from pandas import DataFrame, Series
from spec.enums import MainTableColumns as Cols, EventType
import numpy as np
from itertools import pairwise

class ErrorMetrics:

    ERROR_QUOTIENT: Final[str] = "ErrorQuotient"
    """
    Jadud's Error Quotient (EQ), measuring repeated struggles with compile errors.
    It is assumed that each set or rows passed to the `calculate` method
    represents a single session of compile events, as Jadud does not define
    a session exactly.
    """

    REPEATED_ERROR_DENSITY: Final[str] = "RepeatedErrorDensity"
    """
    Becker's
    """

    COMPILE_ERROR_COUNT: Final[str] = "CompileErrorCount"
    """
    The count of total compile errors in a submission, used by Hoq et al. (2023).
    """

    def __init__(self, is_data_sorted: bool,
                 compile_message_type_column: str = Cols.CompileMessageType,
                 compile_event: str = EventType.Compile,
                 compile_error_event: str = EventType.CompileError
                 ):
        if not is_data_sorted:
            # TODO: Could also have a sort method that sorts the data
            raise ValueError("Data must be sorted calculating Error metrics.")
        self.compile_message_type_column = compile_message_type_column
        self.compile_event = compile_event
        self.compile_error_event = compile_error_event

    def _calculate_paired_compilation_metric(self, rows: DataFrame, scorer) -> float | None:
        # Get all compile events and compile errors
        compiles = rows[rows[Cols.EventType] == self.compile_event]
        compile_errors = rows[rows[Cols.EventType] == self.compile_error_event]

        if len(compiles) >= 1 and len(compile_errors) == 0:
            # ASSUMPTION: If there was at least one successful compile and
            # no compile errors ever, the EQ should be zero, even if there are
            # no pairs to compare.
            # This is not defined by Jadud, but it is a reasonable assumption;
            # otherwise EQ would be undefined in cases where the student is
            # successful on the first try.
            return 0.0

        # Otherwise, if there are no compile events, the EQ is undefined.
        # When aggregating across problems, the caller can choose to average
        # or sum, which will respectively ignore this problem or treat it as zero.
        # It would also be reasonable to return 1.0 here, since the student never
        # resolved their compilation, but Jadud does not specify this.
        if len(compiles) <= 1:
            return None

        # Get consecutive pairs of compile events
        compile_pair_indices = list(pairwise(compiles.index))

        type_tuples = []
        for pair in compile_pair_indices:
            # Get all compile errors associated with compile events e1 and e2
            error_index_1, error_index_2 = pair
            error_event_id_1 = compiles[Cols.EventID].loc[error_index_1]
            error_event_id_2 = compiles[Cols.EventID].loc[error_index_2]

            e1_errors = compile_errors[compile_errors[Cols.ParentEventID] == error_event_id_1]
            e2_errors = compile_errors[compile_errors[Cols.ParentEventID] == error_event_id_2]

            e1_error_types = e1_errors[self.compile_message_type_column].to_list()
            e2_error_types = e2_errors[self.compile_message_type_column].to_list()

            type_tuples.append((e1_error_types, e2_error_types))

        return scorer(type_tuples)


    def _eq_scorer(self, type_tuples: List[Tuple[List[str], List[str]]]) -> float | None:
        score = 0
        for e1_errors, e2_errors in type_tuples:
            score_delta = 0
            if len(e1_errors) > 0 and len(e2_errors) > 0:
                # If both compiles resulted in errors, add 8 to the score
                score_delta += 8

                # Get the set of errors shared by both compiles.
                # Jadud does not specify how to handle multiple errors, so we
                # count a repeated error as any pair of compile errors that share at
                # least one error type.
                shared_errors = set(e1_errors).intersection(set(e2_errors))
                if len(shared_errors) > 0:
                    score_delta += 3

            score += score_delta / 11
        return score / len(type_tuples)

    def calculate_eq(self, rows: DataFrame) -> float | None:
        return self._calculate_paired_compilation_metric(rows, self._eq_scorer)

    def _red_scorer(self, type_tuples: List[Tuple[List[str], List[str]]]) -> float | None:
        red = 0
        # We need to track the number of repeated errors
        repeated = 0
        for e1_errors, e2_errors in type_tuples:
            shared_errors = set(e1_errors).intersection(set(e2_errors))
            if len(shared_errors) > 0:
                # If there is a shared error, we increment the r count
                repeated += 1
            else:
                # Otherwise, there was a new error or no errors, so we add to RED and reset the repeated count
                if repeated > 0:
                    red += (repeated ** 2) / (repeated + 1)
                repeated = 0
        if repeated > 0:
            red += (repeated ** 2) / (repeated + 1)

        # Unlike EQ, RED is not normalized by the number of pairs.
        return red

    def calculate_red(self, rows: DataFrame) -> float | None:
        return self._calculate_paired_compilation_metric(rows, self._red_scorer)

    def calculate(self, rows: DataFrame) -> dict[str, any]:
        error_quotient = self.calculate_eq(rows)
        # TODO: Add Hoq et al.'s error measure
        return Series({
            self.ERROR_QUOTIENT: error_quotient,
            self.REPEATED_ERROR_DENSITY: self.calculate_red(rows),
        })
