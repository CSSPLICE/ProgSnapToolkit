
import os
import copy
from progsnap2.database.codestate.codestate_writer import CodeStateSectionEntry, ContextualCodeStateEntry
from progsnap2.database.codestate.directory_codestate_writer import DirectoryCodeStateWriter
from progsnap2.database.codestate.git_codestate_writer import GitCodeStateWriter
from .conftest import TEMP_DIR, cleanup_temp_dir

temp_dir = TEMP_DIR

class CodestateGenerator():

    def __init__(self, with_grouping_id=True):

        grouping_id = "subject_1" if with_grouping_id else None
        project_id = "project_1"

        self.codestate1 = ContextualCodeStateEntry(
            sections=[
                CodeStateSectionEntry(Code = "print('Hello, World!')", CodeStateSection = "main.py"),
                CodeStateSectionEntry(Code = "def greet(): pass", CodeStateSection = "greet.py")
            ],
            grouping_id=grouping_id,
            ProjectID=project_id
        )

        self.codestate2 = copy.deepcopy(self.codestate1)
        self.codestate2.sections[0].Code = "print('Hello, Universe!')"

        self.codestate3 = copy.deepcopy(self.codestate2)
        self.codestate3.sections[1].Code = "def greet(): print('Hello!')"

gen = CodestateGenerator()
gen_no_grouping = CodestateGenerator(False)

# TODO: Test SQLTableCodeStateWriter!

def test_directory_codestate_writer():
    # Initialize the DirectoryTableWriter
    writer = DirectoryCodeStateWriter(temp_dir)

    # Add the codestate and get its ID
    codestate_id_1 = writer.add_codestate_and_get_id(gen.codestate1)

    # Check if the directory was created
    assert os.path.exists(os.path.join(temp_dir, gen.codestate1.grouping_id, codestate_id_1))

    codestate_id_1_again = writer.add_codestate_and_get_id(gen.codestate1)
    assert codestate_id_1_again == codestate_id_1, "Duplicate codestate should return the same ID"

    codestate_id_2 = writer.add_codestate_and_get_id(gen.codestate2)
    assert os.path.exists(os.path.join(temp_dir, gen.codestate2.grouping_id, codestate_id_2))
    assert codestate_id_2 != codestate_id_1, "Different codestates should return different IDs"

def test_git_codestate_writer_with_subject():
    do_test_git_codestate_writer(True)

def test_git_codestate_writer_without_subject():
    do_test_git_codestate_writer(False)

def do_test_git_codestate_writer(with_subject_id):
    cs_gen = gen if with_subject_id else gen_no_grouping

    # Initialize the DirectoryTableWriter
    writer = GitCodeStateWriter(temp_dir)

    # Add the codestate and get its ID
    codestate_id_1 = writer.add_codestate_and_get_id(cs_gen.codestate1)

    # Check if the directory was created
    path = os.path.join(temp_dir, cs_gen.codestate1.grouping_id or '', cs_gen.codestate1.ProjectID)
    assert os.path.exists(path)

    codestate_id_1_again = writer.add_codestate_and_get_id(cs_gen.codestate1)
    assert codestate_id_1_again == codestate_id_1, "Duplicate codestate should return the same ID"

    codestate_id_2 = writer.add_codestate_and_get_id(cs_gen.codestate2)
    assert codestate_id_2 != codestate_id_1, "Different codestates should return different IDs"


def test_csv_table_codestate_writer(csv_config):
    from progsnap2.database.codestate.table_codestate_writer import CSVTableCodeStateWriter
    from progsnap2.database.sql_context import IOContext

    # Initialize the DirectoryTableWriter
    writer = CSVTableCodeStateWriter(csv_config)

    # Add the codestate and get its ID
    codestate_id_1 = writer.add_codestate_and_get_id(gen.codestate1)

    # Check if the CSV file was created
    assert os.path.exists(csv_config.codestates_table_path)

    codestate_id_1_again = writer.add_codestate_and_get_id(gen.codestate1)
    assert codestate_id_1_again == codestate_id_1, "Duplicate codestate should return the same ID"

    codestate_id_2 = writer.add_codestate_and_get_id(gen.codestate2)
    assert codestate_id_2 != codestate_id_1, "Different codestates should return different IDs"

    # The CSV file should have 4 non-header lines (2 sections * 2 codestates)
    # The CodeState columns should match the expected values
    import csv
    rows = []
    with open(csv_config.codestates_table_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)
    assert len(rows) == 4, "CSV file should have 4 rows (2 codestates * 2 sections)"

    # Check the first codestate
    assert rows[0]['CodeStateID'] == codestate_id_1
    assert rows[0]['Code'] == gen.codestate1.sections[0].Code
    assert rows[0]['CodeStateSection'] == gen.codestate1.sections[0].CodeStateSection

    # Check the second codestate
    assert rows[2]['CodeStateID'] == codestate_id_2
    assert rows[2]['Code'] == gen.codestate2.sections[0].Code
    assert rows[2]['CodeStateSection'] == gen.codestate2.sections[0].CodeStateSection
