"""This module parses the given data into virtual html components"""

import datetime
from datetime import datetime
from typing import Any

import plotly.express as px
from pandas import DataFrame

from helper_functions import count_individuals
from html_components import (HTMLContainer, HTMLHeadline, HTMLiFrame,
                             HTMLParagraph, HTMLTable)


def parse_artists(
    streams: DataFrame,
    count_of_top_artists: int = 10,
    count_of_least_streamed_artists: int = 10,
) -> HTMLContainer:
    """Parses statistics which are related directly to artists and returns an HTMLContainer-Component"""
    artist_container = HTMLContainer()
    top_artists = streams["artistName"].value_counts().head(
        count_of_top_artists + 1)
    least_artists = (
        streams["artistName"].value_counts().tail(
            count_of_least_streamed_artists + 1)
    )

    top_artists_table = HTMLTable(["Artist", "Total Streams"])
    for artist, count in top_artists.items():
        top_artists_table.add_row((artist, count))

    total_streams = len(streams)
    top_x_ratio = round(top_artists.sum() / total_streams * 100, ndigits=2)

    artist_container.add_component(
        HTMLHeadline(
            f"Top {count_of_top_artists} Streamed Artists 👩‍🎨", level=2)
    )
    artist_container.add_component(top_artists_table)
    artist_container.add_component(
        HTMLParagraph(
            f"""
        You have streamed <strong>{streams["artistName"].nunique()}</strong> 
        different artists and clicked the play button <strong>{total_streams}</strong> times.
        This means that in average you streamed every single artist <strong>{round(total_streams / streams["artistName"].nunique(), ndigits=2)}</strong> time(s).
        The streams you generated listening to your top {count_of_top_artists} most listened artists take up <strong>{top_x_ratio}%
        </strong> of your total streams.
        """
        )
    )

    least_streamed_artists_table = HTMLTable(["Artist", "Total Streams"])
    for artist, count in least_artists.items():
        least_streamed_artists_table.add_row((artist, count))
    artist_container.add_component(
        HTMLHeadline(
            f"{count_of_least_streamed_artists} Least Streamed Artists", level=2
        )
    )
    artist_container.add_component(least_streamed_artists_table)

    return artist_container


def parse_songs(streams: DataFrame, count_of_top_songs: int = 10) -> HTMLContainer:
    """Parses statistics which are related directly to songs and returns an HTMLContainer-Component"""
    count_of_songs = streams["trackName"].value_counts().head(
        count_of_top_songs + 1)

    songs_container = HTMLContainer()

    top_songs_table = HTMLTable(["Song", "Total Streams"])
    for song, count in count_of_songs.items():
        top_songs_table.add_row((song, count))
    songs_container.add_component(
        HTMLHeadline(f"Top {count_of_top_songs} Streamed Songs 🎵", level=2)
    )
    songs_container.add_component(top_songs_table)

    avg_listens_per_song = streams["trackName"].value_counts().mean()
    median_listens_per_song = streams["trackName"].value_counts().median()

    # TODO add some kind of streaming distribution diagram (histogram, gaussian curve)

    songs_container.add_component(
        HTMLParagraph(
            f"""
        In average you listened to an individual song <strong>{round(avg_listens_per_song, 1)}</strong> time(s). <br/>
        The median amount of streams per song is <strong>{median_listens_per_song}</strong>
        """
        )
    )

    return songs_container


def parse_playtime(streams: DataFrame) -> HTMLContainer:
    """Parses statistics which are related directly to playtime of the user and returns an HTMLContainer-Component"""

    playtime_container = HTMLContainer()
    playtime_container.add_component(HTMLHeadline("Your Playtime ⌚", level=2))

    # Get the mean playtime per stream
    avg_playtime_per_stream_ms = streams["msPlayed"].mean()
    playtime_container.add_component(
        HTMLParagraph(
            f"Your average playtime per stream is <strong>{round(avg_playtime_per_stream_ms / 1000 / 60, 1)} minutes</strong>."
        )
    )
    playtime_container.add_component(
        HTMLParagraph(
            f"""
        Additionally your longest stream took you about <strong>{round(streams["msPlayed"].max() / 1000 / 60, ndigits=2)} 
        minute(s)</strong> while your shortest stream was just <strong>{round(streams["msPlayed"].min() / 1000 / 60, ndigits=4)}
        </strong> minute(s) long.
        """
        )
    )

    return playtime_container


def parse_dates(streams: DataFrame, path: str) -> HTMLContainer:
    """
    Parses statistics which are related directly to dates the user
    listen to music and returns an HTMLContainer-Component
    """
    # dates = list(map(lambda dt: dt.split(" ")[0], dates))
    # unique_dates = list(set(dates))
    # days_streamed = len(unique_dates)

    # plays_per_day = streams["endTime"].value_counts().head(11)
    dates_table = HTMLTable(["Date", "Streams"])
    for _, date, count in streams["endTime"].apply(
            lambda date_str: date_str.split(" ")[0]).value_counts().reset_index().head(11).itertuples():
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d.%m.%Y")
        dates_table.add_row((formatted_date, count))

    # [ [date, count] ]
    # plays_per_day = []
    # streams_per_day = []
    # for date in unique_dates:
    #    streams = dates.count(date)
    #    plays_per_day.append([date, streams])
    #    streams_per_day.append(streams)

    # plays_per_day.sort(key=(lambda d: d[1]))
    # plays_per_day.reverse()

    #    date = datetime.date.fromisoformat(plays_per_day[i][0])
    #    dates_table.add_row(
    #        (date.strftime("%A %d %B %Y"), plays_per_day[i][1]))

    # streams_in_year = DataFrame(
    #    dict(year=unique_dates, streams=streams_per_day))

    # fig = px.bar(
    #    streams_in_year,
    #    x="year",
    #    y="streams",
    #    title="Amount of streams throughout the year",
    # )
    # fig.write_html(path + "/stream_chart.html")

    dates_container = HTMLContainer()
    dates_container.add_component(
        HTMLHeadline("Top 10 Streams per Day", level=2))
    dates_container.add_component(dates_table)
    return dates_container
    dates_container.add_component(HTMLiFrame(src="stream_chart.html"))
    dates_container.add_component(
        HTMLParagraph(
            f"""
        You streamed from Spotify on <strong>{streams["endTime"]}</strong> different days. Wow that's about 
        {100 - round(days_streamed / 365, ndigits=2)}% of a year.
        """
        )
    )

    return dates_container
