
from dataclasses import dataclass, field
from typing import Callable, Protocol
from analytics.ps2_dataset import LinkTablePreprocessor, PS2Dataset, Preprocessor
from spec.enums import MainTableColumns as Cols, EventType
from enum import Enum

from spec.spec_definition import ProgSnap2Spec

class Granularity(Enum):
    """Granularity of collected data.
    Based on Ihantola et al. (2015), Figure 3
    http://dx.doi.org/10.1145/2858796.2858798
    """

    Submission = "submission"
    """
    The dataset only logs submissions submitted for feedback.
    This also includes commit-level granualrity for git-based datasets.
    """

    Execution = "execution"
    """
    The dataset logs code run events, in addition to code submitted
    for feedback.
    """

    Edit = "edit"
    """
    The dataset logs individual edits to the code, though not at the level
    of individual keystrokes (i.e., there is a limit to the logging frequency, so
    log events can include multiple keystrokes).
    This is equivalent to Ihantola et al.'s "line-level" granularity, but the
    term "edit" is more general, as logs may not occur exactly at the line level.
    """

    Keystroke = "keystroke"
    """
    The dataset logs individual keystrokes, i.e., every key press and release.
    This is the most granular level of logging.
    """

    def __str__(self):
        return self.value

@dataclass
class AnalyticsConfig:
    name: str

    loader: Callable[[str, "AnalyticsConfig", ProgSnap2Spec], PS2Dataset]

    granularity: Granularity
    """The granularity of the events in this dataset."""

    primary_timestamp_column: str
    """The most reliable timestamp columns to use in analysis."""
    primary_problem_grouping_column: str = Cols.ProblemID
    """The most fine-grained problem grouping column to use in analysis (ProblemID or AssignmentID).
    Note: ProblemID will be automatically added to the main table if it is missing, so it
    should typically be safe to use, but this information is provided for clarity.
    """

    main_table_preprocessors: list[Preprocessor] = field(default_factory=list)
    """A list of Preprocessors to apply to the main table before analysis."""
    link_table_preprocessors: list[LinkTablePreprocessor]  = field(default_factory=list)
    """A list of LinkTablePreprocessors to apply to link tables before analysis."""

    attempt_grouping_columns: list[str] = field(default_factory=lambda: [Cols.SubjectID, Cols.AssignmentID, Cols.ProblemID])
    """A list of columns that should be used to group one student working on one problem in one classroom.
    Defaults to [SubjectID, AssignmentID, ProblemID], but may need additional columns.
    """

    submit_event: str = EventType.Submit
    """Event that best resembles a "submission," even if Submissions are not directly logged."""

    # In an ideal world, we wouldn't need these, but some datasets don't have
    # typicaly compilations.
    compile_event: str = EventType.Compile
    """The event that indicates a compilation happened."""
    compile_error_event: str = EventType.CompileError
    """The event that indicates a compilation error occurred."""
    compile_error_type_column: str = Cols.CompileMessageType
    """The column that indicates the broad type of compilation error."""

    grades_link_table_name: str = "Subject"
    """The name of the link table that contains grades."""
    final_grade_column: str = None
    """The column that contains the best summative outcome measure for the student."""

    start_time: str = None
    """A beginning cutoff timestamp for the dataset, e.g. to avoid noisy data."""
    end_time: str = None
    """An ending cutoff timestamp for the dataset, e.g. to avoid noisy data."""

    early_time: str = None
    """
    A timestamp representing an "early" cutoff for the dataset,
    usually between 20% and 40% of the dataset, splitting assignments
    and problems as cleanly as possible.
    """

    def load(self, root_path: str, spec=None) -> PS2Dataset:
        """
        Loads the dataset using the specified root path and spec.
        """
        if self.loader is None:
            raise ValueError("No loader function specified in AnalyticsConfig.")
        return self.loader(root_path, self, spec)
