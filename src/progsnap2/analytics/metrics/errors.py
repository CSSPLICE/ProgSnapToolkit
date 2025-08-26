
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

    FAILED_COMPILE_COUNT: Final[str] = "FailedCompileCount"
    """
    The count of total compiles that had at least one error,
    used by Hoq et al. (2023).
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

    def calculate_failed_compile_count(self, rows: DataFrame) -> int:
        """
        Calculate the total number of compile errors in the given rows.
        This is used by Hoq et al. (2023) as a measure of compile error frequency.
        """
        # We count the ParentEventIDs of compile errors. If there was no
        # error, the ParentEventID will not be included, so this only counts
        # the number of unique compile events that had at least one error.
        return rows[rows[Cols.EventType] == self.compile_error_event][Cols.ParentEventID].nunique()

    def _get_resolution_stats(self, main_table: DataFrame, grouping_cols):
        relevant_event_types = [
            EventType.Compile,
            EventType.CompileError,
        ]
        compile_events = main_table[main_table[Cols.EventType].isin(relevant_event_types)].copy()
        # compile_events.groupby(grouping_cols

        # main_table.groupby(grouping_cols)
        # main_table.groupby(Cols.CompileMessageType).apply()


    # TODO: This version doesn't consider the error type, so the
    # averages aren't error-type-specific.
    def _watwin_time_preprocessing(self, main_table_df):
        # Watson et al. (2013) doesn't state how they get mean and sd, we assume
        # both mean and sd calculated from all compilation pairs

        time_arr = {}
        mean_dict = {}
        std_dict = {}

        subjects = set(main_table_df[Cols.SubjectID])
        timer_index = 1
        for subj in subjects:
            timer_index += 1

            current_df = main_table_df.loc[main_table_df[Cols.SubjectID] == subj]
            compiles = current_df[current_df[Cols.EventType] == self.compile_event]
            compile_errors = current_df[current_df[Cols.EventType] == self.compile_error_event]

            should_check_codestates = current_df[Cols.CodeStateID].notna().any()

            sum_time = 0
            count_time = 0

            if len(compiles) > 1:
                time_arr[subj] = {}
                for i in range(len(compiles) - 1):
                    # Watson(2013) requires pair pruning, in which Remove identical pairs
                    if not should_check_codestates or (compiles[Cols.CodeStateID].iloc[i + 1] != compiles[Cols.CodeStateID].iloc[i]):
                        e1_errors = compile_errors[compile_errors[Cols.ParentEventID] == compiles["EventID"].iloc[i]]
                        # If e1 compile resulted in error
                        if len(e1_errors) > 0:
                            # Watson(2013) requires time estimate preparation before calculating score, we assume no
                            # invocation reported in dataset, which means using time difference of compilcation pairs
                            # directly
                            date1 = compiles[self.time_column].iloc[i + 1]
                            date2 = compiles[self.time_column].iloc[i]
                            time_diff = (date1 - date2).total_seconds()
                            sum_time += time_diff
                            count_time = count_time + 1
                            time_arr[subj][compiles[Cols.CodeStateID].iloc[i]] = time_diff

            if count_time != 0:
                mean_time = sum_time / count_time
                std_time = np.std(np.asarray(list(time_arr[subj].values())))
            else:
                mean_time = 0
                std_time = 0

            mean_dict[subj] = mean_time
            std_dict[subj] = std_time

        return time_arr, mean_dict, std_dict


    def calculate_watwin(session_table):
        # Watson(2013) requires 1) deletion fixes 2) commented fixes during data preparation 3) error message
        # generalization, we assume the dataset has fulfilled this requirement
        session_table = session_table.sort_values(by=['Order'])
        compiles = session_table[session_table[Cols.EventType] == "Compile"]
        compile_errors = session_table[session_table[Cols.EventType] == "Compile.Error"]

        if len(compiles) <= 1:
            return None

        # Begin calculate WatWin scores:
        score = 0
        pair_count = 0

        for i in range(len(compiles) - 1):
            # Only look at consecutive compiles within a single assignment/problem/session
            changed_segments = False
            for segment_id in ["SessionID", "ProblemID", "AssignmentID"]:
                if segment_id not in compiles:
                    continue
                if compiles[segment_id].iloc[i] != compiles[segment_id].iloc[i + 1]:
                    changed_segments = True
                    break
            if changed_segments:
                continue

            pair_count += 1

            # Watson(2013) requires pair pruning, in which Remove identical pairs
            if compiles[Cols.CodeStateID].iloc[i] != compiles[Cols.CodeStateID].iloc[i + 1]:

                # Get all compile errors associated with compile events e1 and e2
                e1_errors = compile_errors[compile_errors[Cols.ParentEventID] == compiles["EventID"].iloc[i]]
                e2_errors = compile_errors[compile_errors[Cols.ParentEventID] == compiles["EventID"].iloc[i + 1]]

                # if former event has error
                if len(e1_errors) > 0:

                    # if later event has error
                    if len(e2_errors) > 0:

                        # Get the set of errors shared by both compiles
                        shared_errors = set(e1_errors["CompileMessageType"]).intersection(
                            set(e2_errors["CompileMessageType"]))

                        # TODO: Don't just use the first compile message - use all
                        # if same full message
                        # We assume the attribute containing full message is CompileMessageData
                        e1_error_message = e1_errors["CompileMessageData"].iloc[0]
                        e2_error_message = e2_errors["CompileMessageData"].iloc[0]
                        if e1_error_message == e2_error_message:
                            score += 4
                            # if same error type
                        if len(shared_errors) > 0:
                            score += 4
                        # TODO: Watson (2013) requires for error line number of compiled code
                        # if same line
                        try:
                            if e1_errors["SourceLocation"].iloc[0].split(':')[1] == \
                                    e2_errors["SourceLocation"].iloc[0].split(':')[1]:
                                score += 2
                        except:
                            out.info("Improperly formatted source location in: [%s, %s]" % (
                                e1_errors["SourceLocation"].iloc[0], e2_errors["SourceLocation"].iloc[0]))

                        # if time < M - 1SD
                        if compiles["TimeEst"].iloc[i] < (
                                compiles["TimeMean"].iloc[i] - compiles["TimeStd"].iloc[i]):
                            score += 1
                        # if time >= M - 1SD
                        else:
                            # if time > M + 1SD
                            if compiles["TimeEst"].iloc[i] > (
                                    compiles["TimeMean"].iloc[i] + compiles["TimeStd"].iloc[i]):
                                score += 25
                            # if time <= M + 1SD
                            else:
                                score += 15
                    # if later event does not have error
                    else:
                        # if time < M - 1SD
                        if compiles["TimeEst"].iloc[i] < (
                                compiles["TimeMean"].iloc[i] - compiles["TimeStd"].iloc[i]):
                            score += 1
                        # if time >= M - 1SD
                        else:
                            # if time > M + 1SD
                            if compiles["TimeEst"].iloc[i] > (
                                    compiles["TimeMean"].iloc[i] + compiles["TimeStd"].iloc[i]):
                                score += 25
                            # if time <= M + 1SD
                            else:
                                score += 15

        if pair_count == 0:
            return None

        watwin = (score / 35.) / (len(compiles) - 1.)
        return watwin


    def calculate(self, rows: DataFrame) -> dict[str, any]:
        error_quotient = self.calculate_eq(rows)
        # TODO: Add Hoq et al.'s error measure
        return Series({
            self.ERROR_QUOTIENT: error_quotient,
            self.REPEATED_ERROR_DENSITY: self.calculate_red(rows),
            self.FAILED_COMPILE_COUNT: self.calculate_failed_compile_count(rows),
        })
