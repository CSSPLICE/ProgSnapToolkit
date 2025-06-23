
from typing import Final
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

    def __init__(self, is_data_sorted: bool, compile_event: str = EventType.Compile.value):
        if not is_data_sorted:
            # TODO: Could also have a sort method that sorts the data
            raise ValueError("Data must be sorted calculating Error metrics.")
        self.compile_event = compile_event


    def calculate_eq(self, rows: DataFrame) -> float | None:
        # Get all compile events and compile errors
        compiles = rows[rows[Cols.EventType] == EventType.Compile]
        compile_errors = rows[rows[Cols.EventType] == EventType.CompileError]

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

        score = 0
        for pair in compile_pair_indices:
            # Get all compile errors associated with compile events e1 and e2
            error_index_1, error_index_2 = pair
            error_event_id_1 = compiles[Cols.EventID].loc[error_index_1]
            error_event_id_2 = compiles[Cols.EventID].loc[error_index_2]

            e1_errors = compile_errors[compile_errors[Cols.ParentEventID] == error_event_id_1]
            e2_errors = compile_errors[compile_errors[Cols.ParentEventID] == error_event_id_2]

            score_delta = 0
            if len(e1_errors) > 0 and len(e2_errors) > 0:
                # If both compiles resulted in errors, add 8 to the score
                score_delta += 8

                # Get the set of errors shared by both compiles.
                # Jadud does not specify how to handle multiple errors, so we
                # count a repeated error as any pair of compile errors that share at
                # least one error type.
                shared_errors = set(e1_errors["CompileMessageType"]).intersection(
                    set(e2_errors["CompileMessageType"])
                )
                if len(shared_errors) > 0:
                    score_delta += 3
            score += score_delta / 11

        return score / len(compile_pair_indices)  # Normalize by the number of pairs

    def calculate(self, rows: DataFrame) -> dict[str, any]:
        error_quotient = self.calculate_eq(rows)
        # TODO: Add Hoq et al.'s error measure
        return Series({
            self.ERROR_QUOTIENT: error_quotient
        })
