import os
import shutil
from git import Repo

from database.codestate.codestate_writer import CodeStateWriter, ContextualCodeStateEntry

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

    def add_codestate_and_get_id(self, codestate: ContextualCodeStateEntry) -> str:
        grouping_id = codestate.grouping_id or ''
        directory = os.path.join(self.root, grouping_id, codestate.ProjectID)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            # create a new git repo in the director
            repo = Repo.init(directory)
        else:
            repo = Repo(directory)

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
