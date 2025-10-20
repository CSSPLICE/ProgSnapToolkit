import os
import shutil
from git import Repo
import pandas as pd
from pandas import DataFrame

from progsnap2.database.codestate.codestate_writer import CodeStateWriter, ContextualCodeStateEntry
from progsnap2.spec.enums import MainTableColumns as Cols, CodeStatesTableColumns as CodeCols

# TODO: Handle locking and other things?
# This would probably require a fair bit of work, may be out of scope
# but I can at least create this MVP for now
# TODO: PyGit creates readonly files, which can cause issues deleting directories
# may be good to document this.
class GitCodeStateWriter(CodeStateWriter):

    def __init__(self, code_states_dir_path: str):
        super().__init__()
        self.root = code_states_dir_path

    def add_codestate_with_id(self, codestate, codestate_id):
        raise NotImplementedError("GitCodeStateWriter does not support add_codestate_with_id.")

    def requires_project_id(self):
        return True

    def get_repo_dir(self, project_id, grouping_id = None):
        grouping_id = grouping_id or ''
        directory = os.path.join(self.root, str(grouping_id), str(project_id))
        return directory

    def get_repo(self, create_if_missing, project_id, grouping_id = None):
        directory = self.get_repo_dir(project_id, grouping_id)
        if not os.path.exists(directory):
            if create_if_missing:
                os.makedirs(directory, exist_ok=True)
                return Repo.init(directory)
            else:
                return None
        return Repo(directory)

    def add_codestate_and_get_id(self, codestate: ContextualCodeStateEntry) -> str:
        directory = self.get_repo_dir(codestate.ProjectID, codestate.grouping_id)
        repo = self.get_repo(True, codestate.ProjectID, codestate.grouping_id)

        # Delete all files not under the .git folder
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if item == ".git":
                continue
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    print(f"Deleted file: {item_path}")
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"Deleted folder: {item_path}")
            except Exception as e:
                # TODO: Handle errors more gracefully
                print(f"Error deleting '{item_path}': {e}")

        # Add the code state to the git repo
        for section in codestate.sections:
            # TODO: Should I force the section to exist (probably not good for Table format / convenience)
            # Or have the config supply a default filename?
            file_path = os.path.join(directory, section.CodeStateSection or self._get_default_codestate_section())
            with open(file_path, 'w') as f:
                f.write(section.Code)

        # Add all files to the repo
        repo.git.add(A=True)

        # Check whether anything has changed or if this is the first commit
        if repo.is_dirty(untracked_files=True) or not repo.head.is_valid():
            # Commit the changes
            repo.index.commit(f"Automatic update")

        # Get the commit hash
        commit = repo.head.commit
        # Return the commit hash as the ID
        hex = commit.hexsha
        repo.close()

        return hex

    def get_codestates_table(self):
        raise ValueError(
            """
            Loading all codestates in Git format is very time consuming.
            For best results, load only a subset of codestates using get_codestates_table_subset(codestate_ids).
            If you need all codestates, you can pass a list of all codestate IDs to that function.
            """
        )

    def do_codestates_have_sections(self):
        raise NotImplementedError("GitCodeStateWriter does not support checking for sections.")

    def get_codestates_table_subset(self, rows: DataFrame) -> DataFrame:
        # TODO: This should be specified in the config, but hard-coding for now to test
        grouping_id = Cols.SubjectID
        grouping_cols = [Cols.ProjectID]
        # When this is configurable, could be none
        if grouping_id is not None:
            grouping_cols.append(grouping_id)
        grouping_cols = [str(c) for c in grouping_cols]
        self._check_dataframe_for_codestate_columns(rows, [Cols.CodeStateID] + grouping_cols)

        parts = []
        for _, group in rows.groupby(grouping_cols, as_index=False):
            part = self._get_codestates_for_repo(group, grouping_id)
            parts.append(part)

        return pd.concat(parts, ignore_index=True)

    def _get_codestates_for_repo(self, rows: DataFrame, grouping_id_col) -> DataFrame:
        # Assumes that all rows share a project/grouping id
        first_row = rows.iloc[0]
        project_id = first_row[str(Cols.ProjectID)]
        grouping_id = None if grouping_id_col is None else first_row[grouping_id_col]

        directory = self.get_repo_dir(project_id, grouping_id)
        repo = self.get_repo(False, project_id, grouping_id)
        if repo is None:
            print(f"Warning: No repository found at: {directory}")
            return None

        code_rows = []

        for code_state_id in rows[Cols.CodeStateID]:
            try:
                commit = repo.commit(code_state_id)
            except Exception as e:
                print(f"Warning: Commit '{code_state_id}' not found in repository at {directory}.")
                continue

            # Get all files in the commit
            tree = commit.tree
            for blob in tree.traverse():
                if blob.type == 'blob':  # Ensure it's a file
                    file_content = blob.data_stream.read().decode('utf-8')
                    section_name = os.path.basename(blob.path)
                    code_rows.append({
                        Cols.CodeStateID: code_state_id,
                        CodeCols.Code: file_content,
                        CodeCols.CodeStateSection: section_name
                    })
        repo.close()
        return DataFrame(code_rows)






