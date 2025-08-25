import json
from collections.abc import Iterable
from collections.abc import Iterator
from itertools import islice
from math import cos
from math import radians
from pathlib import Path
from typing import Any

import numpy as np

ICON_DOMAIN = (0.5, 43, 16.5, 50)
SWISS_EPSG = "epsg:2056"
EARTH_CIRCUMFERENCE_KM = 40075
EARTH_RADIUS_KM = EARTH_CIRCUMFERENCE_KM / 2 * np.pi


def get_nrows_ncols_from_domain_size_and_reskm(
    domain: tuple[float, float, float, float], res_km: float
) -> tuple[int, int]:
    """
    Calculate number of rows and columns for a given domain and resolution in km.
    """
    min_lon, min_lat, max_lon, max_lat = domain
    km_per_degree = EARTH_CIRCUMFERENCE_KM / 360.0
    lat_km = (max_lat - min_lat) * km_per_degree
    avg_lat = (min_lat + max_lat) / 2.0
    lon_km = (max_lon - min_lon) * km_per_degree * cos(radians(avg_lat))
    return lat_km // res_km, lon_km // res_km


def read_file(path: str | Path) -> list[str]:
    """
    Read a file and return its content based on the file extension.

    This function currently supports JSON files. If a JSON file is provided,
    it returns the list of keys from the parsed JSON object.
    """
    path = Path(path)
    if path.suffix == ".json":
        with path.open(encoding="utf-8") as fd:
            return list(json.load(fd).keys())
    raise ValueError(f"Unable to handle {path.suffix}")


def batched(iterable: Iterable[Any], n: int) -> Iterator[tuple[Any, ...]]:
    """
    Batch data into tuples of length n.
    """
    if n < 1:
        raise ValueError("n must be at least one")
    iterator = iter(iterable)
    while batch := tuple(islice(iterator, n)):
        yield batch


def resolution_degrees_to_km(res_lon_deg: float, res_lat_deg: float) -> float:
    """
    Convert resolution from degrees to kilometers.
    """
    distance_km_yaxis = distance_from_coordinates((0, 0), (0, res_lat_deg))
    distance_km_xaxis = distance_from_coordinates((0, 0), (0, res_lon_deg))
    resolution_km = distance_km_yaxis / distance_km_xaxis * distance_km_yaxis
    return resolution_km


def distance_from_coordinates(
    z1: tuple[float, float], z2: tuple[float, float]
) -> float:
    """
    Calculate the distance between two geographical coordinates.
    The Haversine formula is used to compute the distance between two points on the Earth's surface.

    Parameters
    ----------
    z1 : tuple
        A tuple (lon, lat) representing the longitude and latitude of the first location.
    z2 : tuple
        A tuple (lon, lat) representing the longitude and latitude of the second location.

    Returns
    -------
    float
        The distance between the two locations in kilometers.
    """
    lon1, lat1 = z1
    lon2, lat2 = z2
    r = EARTH_RADIUS_KM  # radius of Earth in kilometers
    p = np.pi / 180  # factor to convert degrees to radians
    a = (
        0.5
        - np.cos((lat2 - lat1) * p) / 2
        + np.cos(lat1 * p) * np.cos(lat2 * p) * (1 - np.cos((lon2 - lon1) * p)) / 2
    )
    d = 2 * r * np.arcsin(np.sqrt(a))
    return d
