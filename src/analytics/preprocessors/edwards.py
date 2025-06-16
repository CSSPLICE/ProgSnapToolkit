from analytics.ps2_dataset import Preprocessor
from analytics.ps2_dataset import PS2Dataset
import pandas as pd
from pandas import DataFrame
from spec.enums import MainTableColumns as Cols

class TimeStampToDateTimePreprocessor(Preprocessor):
    """
    Preprocessor that converts the ClientTimestamp column to datetime.
    """

    def apply(self, dataset: PS2Dataset, main_table: DataFrame) -> DataFrame:
        main_table[Cols.ClientTimestamp] = pd.to_datetime(main_table[Cols.ClientTimestamp], unit='ms', utc=True)
        main_table.sort_values(by=[Cols.ClientTimestamp, Cols.EventID], inplace=True)
        return main_table