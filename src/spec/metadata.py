from pydantic import BaseModel
import yaml

# TODO: Automatically generate this from the Metadata spec

class MetadataValues(BaseModel):
    Version: str = "1.0"
    """This property specifies the current version of the ProgSnap 2 standard that these files adhere to. This allows the standard to change over time. ProgSnap2 versions use semantic versioning and should therefore be string values."""

    IsEventOrderingConsistent: bool = False
    """This property specifies whether the events in the main event table are predominantly ordered (within the
    scope specified by the EventOrderScope property) according to a single, globally-consistent clock, such that the ordering of the events in the same scope can (largely) be assumed to reflect their actual temporal order according to that clock. Datasets originating from distributed systems (including client/server systems) might not have a single clock, in which case the value of this property should be false."""

    EventOrderScope: str = None
    """This property specifies the scope of Order column values within the dataset. The possible values are
    Global, Restricted, and None. When the value is Global, the Order column values are intended to be meaningful to determine the order of all events (globally) in the dataset. When the value is Restricted, Order column values are only comparable between events with identical values for all of the columns specified by the EventOrderScopeColumns property. When the value is None, the Order column values should never be assumed to determine an ordering for any events; in other words, the events are not ordered."""

    EventOrderScopeColumns: str = ''
    """This property specifies the main event table columns which define the scope of meaningful comparisons of Order
    column values. This property must be set to a non-empty value if the EventOrderScope property has the value "Restricted". (This property has no significance if EventOrderScope is not "Restricted".) The value of this column is a semicolon-separated list of main event table column names."""

    CodeStateRepresentation: str = "Table"
    """This property specifies which CodeState representation is used by the dataset."""

    ProgramInputLinkTable: str = ''
    """This property specifies the name of the LinkTable that contains columns describing program input, if
    these are contained in a separate table rather than as columns in the MainTable. If they are included in the MainTable, this value should be the empty string."""

    @staticmethod
    def from_yaml_file(file_path: str) -> "MetadataValues":
        """
        Load metadata values from a YAML file.
        :param file_path: Path to the YAML file.
        :return: MetadataValues instance.
        """
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
            return MetadataValues(**data)



