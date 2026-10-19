"""Type definitions for the Spotify Wrapped project"""
from typing import TypedDict


class StreamingRecord(TypedDict):
    """Schema for Spotify streaming history records"""
    artistName: str
    trackName: str
    msPlayed: int
    endTime: str


# Required columns that must exist in streaming DataFrames
REQUIRED_STREAMING_COLUMNS: list[str] = [
    "artistName",
    "trackName",
    "msPlayed",
    "endTime"
]
