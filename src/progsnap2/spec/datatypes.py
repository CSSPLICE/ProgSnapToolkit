from datetime import datetime
from typing import Optional
from enum import Enum

BASE_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
TIMEZONE_FORMAT = "%z"
FRACTIONAL_SECONDS_FORMAT = ".%f"
DEFAULT_TIMESTAMP_FORMAT = BASE_TIMESTAMP_FORMAT + FRACTIONAL_SECONDS_FORMAT + TIMEZONE_FORMAT
TIMESTAMP_FORMATS = [
    BASE_TIMESTAMP_FORMAT,
    DEFAULT_TIMESTAMP_FORMAT,
    BASE_TIMESTAMP_FORMAT + TIMEZONE_FORMAT,
    BASE_TIMESTAMP_FORMAT + FRACTIONAL_SECONDS_FORMAT,
]

def get_current_timestamp(time = None) -> str:
    """
    Get the current timestamp in the appropriate format.
    """
    if not time:
        time = datetime.now()
    return time.astimezone().strftime(DEFAULT_TIMESTAMP_FORMAT)

def parse_timestamp(timestamp: str) -> datetime:
    """
    Parse a timestamp string. Throws an exception if the format is not valid.
    """
    for format in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp, format)
        except ValueError:
            continue
    raise ValueError(f"Invalid timestamp format: {timestamp}. \
                     Expected base format {BASE_TIMESTAMP_FORMAT} with optional fractional seconds and/or timezone.")

def timestamp_has_timezone(timestamp: str) -> bool:
    """
    Check if a timestamp string has a timezone.
    """
    timestamp_formats = [fomat for fomat in TIMESTAMP_FORMATS if TIMEZONE_FORMAT in fomat]
    for format in timestamp_formats:
        try:
            datetime.strptime(timestamp, format)
            return True
        except ValueError:
            continue
    return False

def is_valid_timezone_offset(timezone: str) -> bool:
    """
    Check if a timezone string is a valid offset.
    """
    try:
        datetime.strptime(timezone, TIMEZONE_FORMAT)
        return True
    except ValueError:
        return False

class DBStringLength(Enum):
    Short = "ID",
    Path = "Path",

class PS2Datatype(Enum):

    ID = ("ID", str, "string", DBStringLength.Short)
    URL = ("URL", str, "string", DBStringLength.Path)
    RelativePath = ("RelativePath", str, "string", DBStringLength.Path)
    SourceLocation = ("SourceLocation", str, "string", DBStringLength.Path)
    String = ("String", str, "string") # Arbitrary length
    Integer = ("Integer", int, "number")
    Real = ("Real", float, "number")
    Boolean = ("Boolean", bool, "boolean")
    Timestamp = ("Timestamp", str, "string", DBStringLength.Short)
    # Typescript type for Enums should be custom, so we use None
    Enum = ("Enum", str, None, DBStringLength.Short)

    def __init__(self, label: str, python_type: type, typescript_type: str, max_str_length: Optional[int] = None):
        self.label = label
        self.python_type = python_type
        self.typescript_type = typescript_type
        self.max_str_length = max_str_length

    def validate_value(self, value) -> None:
        """
        Validate the datatype.
        """
        if not isinstance(value, self.python_type):
            raise ValueError(f"Expected {self.python_type}, got {type(value)}")
        if self == PS2Datatype.Timestamp:
            # Throws an exception if the format is not valid
            parse_timestamp(value)
            return True
        elif self == PS2Datatype.String:
            if self.max_str_length is not None and len(value) > self.max_str_length:
                raise ValueError(f"String length exceeds {self.max_str_length} characters")

    @classmethod
    def from_label(cls, label: str) -> "PS2Datatype":
        for member in cls:
            if member.label == label:
                return member
        raise ValueError(f"Unknown PS2Datatype label: {label}")
