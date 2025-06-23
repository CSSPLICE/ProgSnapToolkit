



def extract_features(rows):
    n_logs = len(rows)
    all_rows = rows
    rows = rows[rows.EventType == "Submit"]
    first_submission_time = rows.ServerTimestamp.min()
    count = len(rows)
    incorrect = sum(rows.Score < 1)
    correct = sum(rows.Score >= 1)
    mean_score = rows.Score.mean()
    max_score = rows.Score.max()
    ever_correct = correct > 0
    rows_until_correct = all_rows
    n_logs_until_correct = n_logs
    first_correct_submission_time = None
    if ever_correct:
        first_correct_index = all_rows[all_rows.Score >= 1].index[0]
        rows_until_correct = all_rows[all_rows.index <= first_correct_index]
        n_logs_until_correct = (all_rows.index <= first_correct_index).sum()
        first_correct_submission_time = rows_until_correct.ServerTimestamp.max()
    time_until_correct = count_total_time(rows_until_correct.ServerTimestamp, 60 * 5)
    total_time_s = count_total_time(all_rows.ServerTimestamp, 60 * 5)
    return pd.Series(
        [count, incorrect, correct, mean_score, max_score, ever_correct, time_until_correct, total_time_s, n_logs, n_logs_until_correct, first_submission_time, first_correct_submission_time],
        index=["Count", "Incorrect", "Correct", "MeanScore", "MaxScore", "EverCorrect", "TimeUntilCorrect", "TotalTimeS", "NLogs", "NLogsUntilCorrect", "FirstSubmissionTime", "FirstCorrectSubmissionTime"])