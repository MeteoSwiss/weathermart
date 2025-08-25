import datetime
import logging
import os
import pathlib
import tarfile
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
import pandas as pd
import requests
import xarray as xr
from pyproj import Proj
from pyproj import Transformer

from weathermart.base import BaseRetriever
from weathermart.base import checktype
from weathermart.utils import ICON_DOMAIN


def read_radar_file_or_raise(file: os.PathLike) -> Any:
    """
    Read a file using wradlib and raise an error if the file could not be read.

    Parameters
    ----------
    file : os.PathLike
        Path to the file to be read.

    Returns
    -------
    Any
        The read METRANET data file.

    Raises
    ------
    ImportError
        If the 'wradlib' package is not installed.
    RuntimeError
        If the file read by radlib is empty.
    """
    try:
        import wradlib as wrl
    except ImportError:
        raise ImportError("The 'wradlib' package is required to use the RadarRetriever.")
    try:
        radar_data = wrl.io.hdf.read_opera_hdf5(file)
        return radar_data
    except Exception as e:
        raise RuntimeError(f"File {file} does not exist.", e)


class OperaAPIRadarRetriever(BaseRetriever):
    """
    Class for retrieving and processing Opera radar data from the MeteoFrance API.
    """

    sources = ("OPERA",)
    variables = {
        "TOT_PREC": ["TOT_PREC"],
    }
    url = "https://partner-api.meteofrance.fr/partner/radar/opera/1.0/"
    # the corners of the OPERA radar data are given in lat/lon
    LL_lon, LL_lat = (np.float64(-10.434576838640398), np.float64(31.746215319325056))
    LR_lon, LR_lat = (np.float64(29.421038635578032), np.float64(31.98765027794496))
    UL_lon, UL_lat = (np.float64(-39.5357864125034), np.float64(67.02283275830867))
    UR_lon, UR_lat = (np.float64(57.81196475014995), np.float64(67.62103710275053))
    # the projection definition of the OPERA radar data
    crs = "+proj=laea +lat_0=55.0 +lon_0=10.0 +x_0=1950000.0 +y_0=-2100000.0 +units=m +ellps=WGS84"
    src_proj = Proj(crs)
    # Transform the lat/lon corners to the OPERA radar projection
    lonlat_transformer = Transformer.from_proj(Proj("EPSG:4326"), src_proj, always_xy=True)
    LL_x, LL_y = lonlat_transformer.transform(LL_lon, LL_lat)
    LR_x, LR_y = lonlat_transformer.transform(LR_lon, LR_lat)
    UL_x, UL_y = lonlat_transformer.transform(UL_lon, UL_lat)
    UR_x, UR_y = lonlat_transformer.transform(UR_lon, UR_lat)
    # The grid is regular in the radar projection (at least we assume so)
    x = np.linspace(LL_x, LR_x, 1900)
    y = np.linspace(LL_y, UL_y, 2200)

    # target grid: Regular lat lon grid
    custom_target_grid = xr.Dataset(
        {"x": np.arange(ICON_DOMAIN[0], ICON_DOMAIN[2], 0.01), "y": np.arange(ICON_DOMAIN[1], ICON_DOMAIN[3], 0.01)},
        attrs={
            "grid_mapping": {
                "epsg_code": "4326",
            },
            "source": "Custom grid",
        },
    )

    def process_radar_file(self,radar_file: pathlib.Path, remove_clutter: bool = True) -> xr.Dataset:
        """
        Process a single OPERA radar file and return an xarray.Dataset.

        Parameters
        ----------
        radar_file : pathlib.Path
            Path to the radar file.
        remove_clutter : bool, optional
            If True, remove clutter (nan values, values over 150 mm/h) from the radar data. Default is True.

        Returns
        -------
        xr.Dataset
            Dataset containing the radar data with dimensions ('time', 'y', 'x').
        """
        radar_data = read_radar_file_or_raise(radar_file)
        header = radar_data["dataset1/what"]
        timestamp = datetime.datetime.strptime(
            (radar_data["what"]["date"] + radar_data["what"]["time"]).decode(), "%Y%m%d%H%M%S"
        )
        nodata = header["nodata"]
        undetect = header["undetect"]
        values = radar_data["dataset1/data1/data"]
        # TODO: agree on solution here
        # https://www.mdpi.com/2073-4433/10/6/320 (paper about OPERA)
        # there is both "nodata" (i.e. it is not in range of any radar)
        if remove_clutter:
            values[values == nodata] = np.nan
            # and "undetect" (i.e. it is in range of a radar but no rain was detected, this is the normal no-rain case)
            values[values == undetect] = 0
            # also, sometimes there are very high values (around 300).
            values[values > 150] = 0
        else:
            logging.warning("Warning: Clutter is not removed from the OPERA radar data.")

        ds = xr.Dataset(
            {"TOT_PREC": (("time", "y", "x"), values[None, ::-1, :])},
            coords={
                "y": self.y,
                "x": self.x,
                "time": [timestamp],
            },
        )

        if not remove_clutter:
            ds["TOT_PREC"].attrs["nodata"] = nodata
            ds["TOT_PREC"].attrs["undetect"] = undetect
        else:
            ds["TOT_PREC"].attrs["nodata"] = "nan"
            ds["TOT_PREC"].attrs["undetect"] = 0

        return ds


    def retrieve(
        self,
        source: str,
        variables: list[tuple[str, dict]],
        dates: datetime.date | str | pd.Timestamp | list[Any],
        meteofranceapi_token_path: os.PathLike | None = None,
    ) -> xr.Dataset:
        """
        Retrieve OPERA radar data for specified dates and variables.

        Parameters
        ----------
        source : str
            Source identifier for the data retrieval process.
        variables : list of tuple[str, dict]
            List of tuples containing variable names and associated parameters.
        dates : list of datetime.date or datetime.date
            Date or list of dates for which to retrieve radar data.
        meteofranceapi_token_path : str, optional
            Path to the file containing the MeteoFrance API token. Default is None.

        Returns
        -------
        xr.Dataset
            Merged dataset containing the radar data for all specified dates and variables.
        Raises
        ------
        RuntimeError
            If the meteofranceapi_token_path is not set or if the token file cannot be read.
        FileNotFoundError
            If the token file is not found.

        """
        logging.warning(
            "The MeteoFrance API Retriever is not fully implemented. Be careful when using data from this retriever."
        )
        if meteofranceapi_token_path is None:
            token = os.getenv("METEOFRANCE_API_TOKEN")
            if token is None:
                raise RuntimeError(
                    "The meteofranceapi_token_path is not set. Please provide a path to the token file as arg or set the METEOFRANCE_API_TOKEN environment variable."
                )
        else:
            try:
                with open(meteofranceapi_token_path) as f:
                    token = f.read().strip()
            except FileNotFoundError:
                raise FileNotFoundError(f"Token file not found: {meteofranceapi_token_path}")
            except Exception as e:
                raise RuntimeError(f"Error reading token file: {e}") from e

        headers = {"apikey": token}

        dates, variables = checktype(dates, variables)

        for date in dates:
            with TemporaryDirectory() as tmpdirname:
                url = f"{self.url}archive/odyssey/composite/RAINFALL_RATE/{date.strftime('%Y-%m-%d')}?format=HDF5"
                request = requests.get(url, headers=headers)
                if request.status_code != 200:
                    raise RuntimeError(f"Failed to retrieve data: {request.status_code} - {request.text}")
                with open(tmpdirname + "file.tar", "wb") as f:
                    f.write(request.content)
                # untar
                with tarfile.open(tmpdirname + "file.tar", "r") as tar:
                    tar.extractall(tmpdirname)
                # process the files
                files = sorted(pathlib.Path(tmpdirname).glob("*.h5"))
                radar_dataarrays = []
                for file in files:
                    radar_dataarrays.append(self.process_radar_file(file))
                radar_dataset = xr.concat(radar_dataarrays, dim="time")
                # todo: regrid to desired grid, metadata, etc.
                return radar_dataset
        raise RuntimeError("No data found for the given dates.")
