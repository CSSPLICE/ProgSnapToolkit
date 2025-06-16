
# TODO: This should use the appropriate reader to get the data.
# and apply appropriate preprocessing steps, e.g. sorting
# and provide convenience methods.

from abc import ABC, abstractmethod
from pandas import DataFrame
from pandas.api.types import is_datetime64_any_dtype as is_datetime
from database.config import PS2DataConfig
from database.writer.db_writer_factory import IOFactory
from spec.enums import MainTableColumns as Cols, MetadataProperties as MetadataProps, EventOrderScope
from spec.spec_definition import ProgSnap2Spec
from spec import datatypes

class Preprocessor(ABC):
    """
    Base class for preprocessors that can be applied to the main table.
    Subclasses should implement the `apply` method.
    """

    @abstractmethod
    def apply(self, dataset: "PS2Dataset", main_table: DataFrame) -> DataFrame:
        """
        Apply preprocessing to the DataFrame.
        :param main_table: The DataFrame to preprocess.
        :return: The preprocessed DataFrame.
        """
        pass

class LinkTablePreprocessor(ABC):
    """
    Base class for preprocessors that can be applied to the link table.
    """

    @abstractmethod
    def apply(self, dataset: "PS2Dataset", link_table_name, link_table: DataFrame) -> DataFrame:
        """
        Apply preprocessing to the link table.
        """
        pass



class PS2Dataset:

    def __init__(self, spec: ProgSnap2Spec, data_config: PS2DataConfig):
        self.spec = spec
        self.data_config = data_config
        self.factory = IOFactory.create_factory(data_config)
        self._main_table: DataFrame = None
        self._metadata_table: DataFrame = None
        self.main_table_preprocessors = [
            SortPreprocessor(),
            TimePreprocessor(),
        ]
        self.link_table_preprocessors = []

        self.get_metadata_table()

    def get_metadata_table(self) -> DataFrame:
        """
        Returns the metadata table as a DataFrame.
        """
        if self._metadata_table is not None:
            return self._metadata_table.copy()
        try:
            with self.factory.create_reader() as reader:
                self._metadata_table = reader.get_metadata_table()
        except FileNotFoundError:
            # If the metadata table is not found, create an empty one
            self._metadata_table = DataFrame()
            print("Warning: Metadata table not found, creating an empty metadata table.")
        return self._metadata_table.copy()

    def get_metadata_property(self, property_name: str) -> any:
        """
        Returns the value of a metadata property.
        :param property_name: The name of the metadata property.
        :return: The value of the metadata property, or None if not found.
        """
        if property_name in self._metadata_table.columns:
            return self._metadata_table[property_name].iloc[0]
        property = self.spec.metadata.get_property(property_name)
        if property is not None:
            print(f"Warning: Metadata property '{property_name}' not found in the dataset, using default value: {property.default_value}")
            return property.default_value
        raise ValueError(f"Metadata property '{property_name}' not found in the dataset.")

    def get_main_table(self) -> DataFrame:
        """
        Returns the main table as a DataFrame.
        """
        if self._main_table is not None:
            return self._main_table.copy()
        with self.factory.create_reader() as reader:
            self._main_table = reader.get_main_table()
        for preprocessor in self.main_table_preprocessors:
            self._main_table = preprocessor.apply(self, self._main_table)
        return self._main_table.copy()

    def get_link_table(self, table_name: str) -> DataFrame:
        """
        Returns the link table as a DataFrame.
        """
        with self.factory.create_reader() as reader:
            link_table = reader.get_link_table(table_name)
        for preprocessor in self.link_table_preprocessors:
            link_table = preprocessor.apply(self, table_name, link_table)
        return link_table


class SortPreprocessor(Preprocessor):
    """
    Preprocessor that sorts the DataFrame according to the metadata.
    """

    def apply(self, dataset: PS2Dataset, main_table: DataFrame) -> DataFrame:
        if Cols.Order not in main_table.columns:
            return main_table
        if not dataset.get_metadata_property(MetadataProps.IsEventOrderingConsistent):
            return main_table
        order_scope = dataset.get_metadata_property(MetadataProps.EventOrderScope)
        if order_scope == EventOrderScope.Global:
            # If the table is globally ordered, sort it
            main_table.sort_values(by=[Cols.Order], inplace=True)
        elif order_scope == EventOrderScope.Restricted:
            # If restricted ordered, sort first by grouping columns, then by order
            order_columns = self.get_metadata_property(MetadataProps.EventOrderScopeColumns)
            if order_columns is None or len(order_columns) == 0:
                raise Exception('EventOrderScope is restricted but no EventOrderScopeColumns given')
            columns = order_columns.split(';')
            columns.append('Order')
            # The result is that _within_ these groups, events are ordered
            self.main_table.sort_values(by=columns, inplace=True)
        return main_table

class TimePreprocessor(Preprocessor):
    """
    Preprocessor that converts time columns to datetime format.
    """

    def apply(self, dataset: PS2Dataset, main_table: DataFrame) -> DataFrame:
        self._convert_time_columm(main_table, Cols.ClientTimestamp, "ClientTimezone")
        self._convert_time_columm(main_table, Cols.ServerTimestamp, "ServerTimezone")
        return main_table

    def _convert_time_columm(self, main_table: DataFrame, time_column_name: str, timezone_column_name: str) -> None:
        if not time_column_name in main_table.columns:
            return


        if is_datetime(main_table[time_column_name]):
            # If the column is already in datetime format, no conversion needed
            return

        timestamp_strings = main_table[time_column_name]

        if timezone_column_name in main_table.columns:
            timezone_strings = list(main_table[timezone_column_name])
            failed_timezone_message = None
            for i in range(len(timezone_strings)):
                if not datatypes.is_valid_timezone_offset(timestamp_strings[i]):
                    failed_timezone_message = f"Warning: Invalid timezone offset '{timezone_strings[i]}' for '{time_column_name}' value '{timestamp_strings[i]}'. Skipping future warnings."
                    timezone_strings[i] = ''
            if failed_timezone_message:
                print(failed_timezone_message)

            timestamp_strings = timestamp_strings.str.cat(timezone_strings, sep='')

        converted = []
        for i in range(len(timestamp_strings)):
            try:
                converted.append(datatypes.parse_timestamp(timestamp_strings[i]))
            except ValueError as e:
                print(f"Warning: Could not parse '{time_column_name}' value '{timestamp_strings[i]}': {e}")
                print("Column will use string values instead.")
                break

        # print(f"Converted {len(converted)} values for '{time_column_name}' column.")

        if len(converted) == len(timestamp_strings):
            main_table[time_column_name] = converted
