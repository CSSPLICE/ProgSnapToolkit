import logging
logger = logging.getLogger(__name__)

from progsnap2.spec.enums import MainTableColumns as Cols
import matplotlib.pyplot as plt

def filter_before_time(main_table, time_cutoff, timestamp_col, filter_problems=True, verbose=True):
    data_subset = main_table[main_table[timestamp_col] <= time_cutoff]

    if filter_problems:
        data_subset = filter_out_partial_problems(main_table, data_subset, time_cutoff, timestamp_col, verbose=verbose)

    if not verbose:
        return data_subset

    logger.info("Semester start", main_table[timestamp_col].min())
    logger.info("Semester end", main_table[timestamp_col].max())
    logger.info("Early cutoff time", time_cutoff)
    if Cols.AssignmentID in data_subset.columns:
        logger.info("Early Assignment IDs:", data_subset[Cols.AssignmentID].unique())
    if Cols.ProblemID in data_subset.columns:
        logger.info("Early Problem IDs:", data_subset[Cols.ProblemID].unique())
    logger.info("Total number of rows:", len(data_subset))
    logger.info("Percent of logs: ", len(data_subset) / len(main_table) * 100)
    if Cols.AssignmentID in data_subset.columns:
        logger.info(f"Assignments: {len(data_subset[Cols.AssignmentID].unique())} / {len(main_table[Cols.AssignmentID].unique())}")
    if Cols.ProblemID in main_table.columns:
        logger.info(f"Problems: {len(data_subset[Cols.ProblemID].unique())} / {len(main_table[Cols.ProblemID].unique())}")
    return data_subset

def filter_out_partial_problems(main_table, data_subset, time_cutoff, timestamp_col, cutoff=0.5, verbose=True):
    included_problem_ids = data_subset[Cols.ProblemID].unique()
    problem_percentages = main_table[main_table[Cols.ProblemID].isin(included_problem_ids)].groupby(Cols.ProblemID).apply(lambda x: (x[timestamp_col] < time_cutoff).mean())
    problem_percentages.sort_values(ascending=False, inplace=True)

    precluded_problems = problem_percentages[problem_percentages < cutoff].index
    len_before = len(data_subset)
    data_subset = data_subset[~data_subset[Cols.ProblemID].isin(precluded_problems)]

    if not verbose:
        return data_subset

    problem_percentages.hist()
    plt.xlabel("Percentage of logs before cutoff time")
    plt.ylabel("Number of problems")
    plt.title("Distribution of problem log percentages")
    plt.show()

    logger.info(f"Removing partial problems: {precluded_problems}")
    logger.info(f"This removed {100 - 100 * len(data_subset) / len_before:.2f}% of data")

    return data_subset