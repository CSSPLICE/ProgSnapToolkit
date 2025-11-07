from progsnap2.analytics.ps2_dataset import PS2Dataset
from progsnap2.spec.enums import CoreTables, MetadataProperties
import sqlite3
import pandas as pd
import os

def to_sqlite(dataset: PS2Dataset, path: str, replace: bool):
    if os.path.exists(path):
        if not replace:
            raise FileExistsError(f"File {path} already exists and replace is set to False.")
        os.remove(path)
    conn = sqlite3.connect(path)
    try:
        metadata_df = dataset.get_metadata_table(False)
        _save_dataframe_to_sqlite(metadata_df, CoreTables.MetadataTable.value, conn)
    except NotImplementedError:
        print("Warning: Metadata table not available in the dataset or config; skipping.")
    for link_table_name in dataset.get_link_table_names():
        df = dataset.get_link_table(link_table_name)
        if not link_table_name.startswith('Link'):
            print(f"Info: Renaming link table name '{link_table_name}' to 'Link{link_table_name}'.")
            link_table_name = 'Link' + link_table_name
        _save_dataframe_to_sqlite(df, link_table_name, conn)
    try:
        codestates_df = dataset.get_codestates()
        _save_dataframe_to_sqlite(codestates_df, CoreTables.CodeStatesTable.value, conn)
    except NotImplementedError:
        repr = dataset.get_metadata_property(MetadataProperties.CodeStateRepresentation.value)
        print(f"Warning: Codestates not available for CodeStateRepresentation '{repr}'; skipping codestates table.")
    _save_dataframe_to_sqlite(dataset.get_main_table(), CoreTables.MainTable.value, conn)

def _save_dataframe_to_sqlite(df: pd.DataFrame, table_name: str, conn: sqlite3.Connection):
    df.to_sql(table_name, conn, if_exists='replace', index=False)