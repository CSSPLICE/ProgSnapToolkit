import logging
logger = logging.getLogger(__name__)

# TODO: This should use the appropriate reader to get the data.
# and apply appropriate preprocessing steps, e.g. sorting
# and provide convenience methods.

import pandas as pd

from abc import ABC, abstractmethod
from pandas import DataFrame
from pandas.api.types import is_datetime64_any_dtype as is_datetime
from progsnap2.database.config import PS2DataConfig
from progsnap2.database.writer.db_writer_factory import IOFactory
from progsnap2.spec.enums import MainTableColumns as Cols, MetadataProperties as MetadataProps, EventOrderScope
from progsnap2.spec.spec_definition import ProgSnap2Spec
from progsnap2.spec import datatypes

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
        self._main_table: DataFrame | None = None
        # Factory now handles loading metadata
        self.metadata_values = self.factory.db_config.metadata
        self.main_table_preprocessors = [
            # SortPreprocessor(), # Can be quite expensive, so disabled by default
            AddProblemIDPreprocessor(),
            TimePreprocessor(),
        ]
        self.link_table_preprocessors = []

    def get_metadata_property(self, property_name: str) -> any:
        """
        Returns the value of a metadata property.
        :param property_name: The name of the metadata property.
        :return: The value of the metadata property, or None if not found.
        """
        if not hasattr(self.metadata_values, property_name):
            logger.warning(f"Warning: Metadata property '{property_name}' not found.")
            return None
        return getattr(self.metadata_values, property_name)

    def get_metadata_table(self, raw: bool) -> DataFrame:
        """
        Returns the metadata table as a DataFrame.
        :param raw: If True, returns the raw metadata table from the dataset, without any processing.
                    Otherwise, gets values from the config as well.
        :return: The metadata table as a DataFrame with Property and Value columns.
        """
        if raw:
            with self.factory.create_reader() as reader:
                return reader.get_metadata_table()

        # Return metadata from config
        metadata_dict = {
            "Property": list(self.metadata_values.__dict__.keys()),
            "Value": list(self.metadata_values.__dict__.values())
        }
        return pd.DataFrame(metadata_dict)

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

    def get_main_table_head(self, n_rows: int = 5) -> DataFrame:
        """ Returns the first `n_rows` of the main table.
        This is useful for quickly inspecting the dataset without
        loading the entire table into memory.
        Rows are loaded in the order they appear in the main table.
        """
        if self._main_table is not None:
            return self.get_main_table().head(n_rows)
        with self.factory.create_reader() as reader:
            head = reader.get_main_table_head(n_rows)
        for preprocessor in self.main_table_preprocessors:
            head = preprocessor.apply(self, head)
        return head

    def get_link_table_names(self) -> list[str]:
        """
        Returns the names of the link tables in the dataset.
        """
        with self.factory.create_reader() as reader:
            return reader.get_link_table_names()

    def get_link_table(self, table_name: str) -> DataFrame:
        """
        Returns the link table as a DataFrame.
        """
        with self.factory.create_reader() as reader:
            link_table = reader.get_link_table(table_name)
        for preprocessor in self.link_table_preprocessors:
            link_table = preprocessor.apply(self, table_name, link_table)
        return link_table

    def add_codestates(self, dataframe: DataFrame) -> DataFrame:
        """
        Merges the CodeStates table with the given DataFrame on the CodeStateID column.
        Note that if the CodeStates table has CodeStateSections, this will raise an error,
        since this would result in multiple rows per CodeStateID in the result, which is
        like not the intended behavior.
        """
        if Cols.CodeStateID not in dataframe.columns:
            raise Exception(f"Cannot add CodeState column: {Cols.CodeStateID} column not found in DataFrame.")
        codestates = self.get_codestates(dataframe)
        if Cols.CodeStateSection in codestates.columns:
            if codestates.groupby(Cols.CodeStateID).size().max() > 1:
                raise Exception("Cannot add CodeStates: CodeStates table has sections, which would result in multiple rows per CodeStateID.")
        return dataframe.merge(codestates, on=Cols.CodeStateID, how='left')

    def get_codestates(self, rows: DataFrame | None = None) -> DataFrame:
        """
        Returns the CodeStates table as a DataFrame, optionally collecting
        only a subset rows matching the CodeStateID in the given DataFrame.
        This is useful for larger datasets, where all CodeStates may not
        easily fit in memory.
        """
        with self.factory.create_reader() as reader:
            if rows is None:
                return reader.get_codestates_table()
            else:
                return reader.get_codestates_table_subset(rows)


class SortPreprocessor(Preprocessor):
    """
    Preprocessor that sorts the DataFrame according to the metadata.
    """

    def __init__(self, sort_column: str = Cols.Order.value):
        self.sort_column = sort_column

    def apply(self, dataset: PS2Dataset, main_table: DataFrame) -> DataFrame:
        if self.sort_column not in main_table.columns:
            logger.warning(f"Warning: Column '{self.sort_column}' not found in the main table, skipping sorting.")
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
            columns.append(self.sort_column)
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
                logger.warning(failed_timezone_message)

            timestamp_strings = timestamp_strings.str.cat(timezone_strings, sep='')

        converted = []
        for i in range(len(timestamp_strings)):
            try:
                converted.append(datatypes.parse_timestamp(timestamp_strings.iloc[i]))
            except ValueError as e:
                logger.warning(f"Warning: Could not parse '{time_column_name}' value '{timestamp_strings.iloc[i]}': {e}")
                logger.warning("Column will use string values instead.")
                break

        # logger.info(f"Converted {len(converted)} values for '{time_column_name}' column.")

        if len(converted) == len(timestamp_strings):
            main_table[time_column_name] = converted

class FilterPreprocessor(Preprocessor):
    """
    Preprocessor that filters columns in the DataFrame.
    """

    def __init__(self, filter_column: str, filter_value):
        self.filter_column = filter_column
        self.filter_value = filter_value

    def apply(self, dataset: PS2Dataset, main_table: DataFrame) -> DataFrame:
        """
        Filters the DataFrame to keep only the specified columns.
        """
        return main_table[main_table[self.filter_column] == self.filter_value].copy()

class AddProblemIDPreprocessor(Preprocessor):
    """
    Preprocessor that adds a ProblemID column to the DataFrame if it is
    missing and the AssignmentID column is present.
    """

    def apply(self, dataset: PS2Dataset, main_table: DataFrame) -> DataFrame:
        """
        Adds a ProblemID column to the DataFrame.
        """
        if Cols.ProblemID not in main_table.columns and Cols.AssignmentID in main_table.columns:
            main_table[Cols.ProblemID] = main_table[Cols.AssignmentID]
        return main_table