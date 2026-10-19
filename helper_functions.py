from typing import Any
import pandas as pd
import glob
import os
from stream_types import REQUIRED_STREAMING_COLUMNS


def count_individuals(elements: list[Any]) -> list[tuple[Any, int]]:
    unique_elements: list[Any] = list(set(elements))
    count_per_element: list[tuple[Any, int]] = []
    for element in unique_elements:
        count_per_element.append((element, elements.count(element)))
    return count_per_element


def read_histories(data_dir: str) -> pd.DataFrame:
    """Reads streaming histories from StreamingHistory*.json files and merges them

    Args:
        data_dir: Directory containing StreamingHistory*.json files

    Returns:
        Merged DataFrame with all streaming history records

    Raises:
        FileNotFoundError: If no StreamingHistory files are found
        ValueError: If required columns are missing from the data
    """
    pattern = os.path.join(data_dir, "StreamingHistory*.json")
    streaming_files = glob.glob(pattern)

    if not streaming_files:
        raise FileNotFoundError(
            f"No StreamingHistory files found in {data_dir}. "
            f"Expected files matching pattern 'StreamingHistory*.json'"
        )

    dataframes: list[pd.DataFrame] = []
    for file_path in streaming_files:
        df = pd.read_json(file_path)
        dataframes.append(df)

    merged_df = pd.concat(dataframes, ignore_index=True)

    missing_columns = [
        col for col in REQUIRED_STREAMING_COLUMNS if col not in merged_df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Missing required columns in streaming data: {missing_columns}. "
            f"Expected columns: {REQUIRED_STREAMING_COLUMNS}"
        )

    return merged_df
