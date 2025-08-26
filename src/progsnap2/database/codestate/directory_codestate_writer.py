
import os
from database.codestate.codestate_writer import CodeStateWriter, ContextualCodeStateEntry


class DirectoryCodeStateWriter(CodeStateWriter):

    def __init__(self, code_states_dir_path: str):
        super().__init__()
        self.root = code_states_dir_path

    def add_codestate_and_get_id(self, codestate: ContextualCodeStateEntry) -> str:
        codestate_id = self.get_codestate_id_from_hash(codestate)
        self.add_codestate_with_id(codestate, codestate_id)
        return codestate_id

    def add_codestate_with_id(self, codestate: ContextualCodeStateEntry, codestate_id: str):
        grouping_id = codestate.grouping_id or ''
        directory = os.path.join(self.root, grouping_id, codestate_id)
        if os.path.exists(directory):
            # Directory already exists, no need to add it again
            return

        os.makedirs(directory, exist_ok=True)
        for section in codestate.sections:
            file_path = os.path.join(directory, section.CodeStateSection or self._get_default_codestate_section())
            with open(file_path, 'w') as f:
                f.write(section.Code)
