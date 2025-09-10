# Program Snapshot Data Toolkit

This codebase serves as a starting point for collecting, sharing and analyzing log data collected from students or users writing programs, including snapshots of code. Specifically, it supports collecting and analyzing data in the common [ProgSnap2 format](https://cssplice.org/progsnap2/) ([Price et al, 2020](https://dl.acm.org/doi/10.1145/3341525.3387373)). The goal of the work is to support computing education research, educational data mining and learning analytics, and it is presented as part of the [SPLICE project](https://cssplice.org/).

Possible use-cases include:
* **Analytics**: I have a research question that I want to answer using programming log data.
  * The Toolkit connects with a number of ready-to-analyze datasets in a shared format, and provides starter code and examples for how to dig into them.
* **Getting Started**: I want to see some examples of what programming log data analysis can do, and build on others' work rather than starting from scratch.
  * The Toolkit provides analysis code from prior work and examples of how to apply it so you can get started.
* **Replication**: I just found something interesting in my own programming dataset, and I want to know if the finding generalizes.
  * The Toolkit helps you replicate your analysis across diverse, multi-institutional datasets, and even to contribute your analysis back to the community in a reusable way.
* **Data Collection**: I'm planning to run a study and collect programming data.
  * The Toolkit offers a customizable starting point for a logger that follows best practices for capturing all the events and event properties you and others will need to understand your data. It uses the ProgSnap2 format, which is compatible with all analytics code provided in this repository.
* **Data Sharing**: I have a dataset and I want to share it. How can I make it most useful to others?
  * The Toolkit offers tools for converting data from any format to the common ProgSnap2 format, making it easier for others to analyze your code. It also offers best practices on how to document your dataset for sharing.

The toolkit is broken into a number of modules, which are largely for data collection and data analysis

# Quickstart

TODO

# Data Collection

TODO

# Data Analysis

## datasets

This module provides configuration files for loading existing public CS education datasets, including:
* [CodeWorkout / 2nd CSEDM Data Challenge Dataset](https://sites.google.com/ncsu.edu/csedm-dc-2021/dataset?authuser=0): `codeworkout`, including S19 and F19 semesters.
* [Falconcode](https://falconcode.dfcs-cloud.net/)
* [Codebench](https://codebench.icomp.ufam.edu.br/dataset/), including the S24 semester (more to be added)
* [Edwards' Keystroke Datasets](https://files.eric.ed.gov/fulltext/EJ1383373.pdf), including S19, F19 and F21.

They are described in more detail in [this document](https://docs.google.com/document/d/1zqO6hIFAUS1aEJ5TVaoMes_d4Oyearg8buLIC-Dfygk/edit?tab=t.0).

Example usage:
```python
from progsnap2.datasets import codeworkout

# Gets the configuration file for the F19 semester
# of the codeworkout dataset
config = codeworkout.F19
# Load the dataset, using the config
dataset = config.load('path/to/root/directory')

# Reads the first 20 rows of the main table
dataset.get_main_table_head(20)
```

The config itself contains other useful information, beyond just for loading the dataset, for example:
* `programming_language`: The programming language used by the dataset
* `granularity`: The granularity at which snapshots were collected (e.g., submission-level, keystroke-level)
* `grades_link_table_name` / `final_grade_column`: The LinkTable and column where students' final grade is stored (if available)
* Which columns are recommended to use to identify timestamps, problems, etc.

## analytics

TODO

## converters

TODO