

from pydantic import BaseModel


class CodeStateSectionEntry(BaseModel):
    """
    A class representing the state of a file at a given time.
    """
    Code: str
    CodeStateSection: str = None

BLANK_CODESTATE_ID = ""

class CodeStateEntry(BaseModel):
    """
    A class representing the state of a whole project at a given time.
    """
    sections: list[CodeStateSectionEntry]
    is_blank: bool = False

    @classmethod
    def from_code(cls, code: str) -> "CodeStateEntry":
        return cls(sections=[CodeStateSectionEntry(Code=code)])