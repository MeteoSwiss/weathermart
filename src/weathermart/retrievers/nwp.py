import datetime
import logging
import pathlib
from itertools import chain
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr
from meteodata_lab import _geo_coords
from meteodata_lab import data_source
from meteodata_lab import grib_decoder

from weathermart.base import BaseRetriever
from weathermart.base import checktype
from weathermart.retrievers.fdb_base import FDBRetriever
from weathermart.utils import variables_metadata

nwp_dic = {
    k: [k] for k in variables_metadata[variables_metadata.source=="ECCODES_COSMO"].short_name.unique()
}
class GribDataRetriever(BaseRetriever):
    """
    Retriever for grib data stored on disk.
    """

    def __init__(self, path: Path | str) -> None:
        self.type_mapping = {
            "forecast": "FCST",
            "analysis": "ANA",
            "first_guess": "FG"
        }
        self.prefix_mapping = {
            "ICON-CH1-EPS": "i1",
            "COSMO-1E": "c1",
            "COSMO-2E": "c2"
        }
        self.ensemble_mapping: dict[str | int | None, str | None] = {
            None: None,
            "all": "*",
            "median": "median",
            "mean": "mean",
            "det": "det",
        }
        for i in range(10):
            self.ensemble_mapping[str(i)] = f"{i:03}"
            self.ensemble_mapping[i] = f"{i:03}"

        self.path = path #pathlib.Path("/store_new/mch/msopr/osm")
        self.sources = ("KENDA-CH1", "ICON-CH1-EPS", "COSMO-1E", "COSMO_2E")
        variable_file = Path(__file__).parent.parent / "cosmo.csv"
        self.variables = nwp_dic
        self.crs = "epsg:4326"

    @staticmethod
    def handle_metadata(ds: xr.Dataset) -> xr.Dataset:
        for variable in ds.data_vars:
            xa = ds[variable]
            if "metadata" in xa.attrs:
                logging.warning(
                    "WrappedMetaData object from earthkit found in xarray attributes for %s. Transforming to dict to save in zarr format.",
                    variable,
                )
                meta = xa.attrs["metadata"].metadata
                xa.attrs["metadata"] = dict(meta)
                for k, v in dict(meta).items():
                    if isinstance(v, np.ndarray):
                        xa.attrs["metadata"][k] = v.tolist()
            ds[variable] = xa

        for c in ds.coords:
            if "metadata" in ds[c].attrs:
                logging.warning(
                    "WrappedMetaData object from earthkit found in xarray attributes for coord %s. Transforming to dict to save in zarr format.",
                    c,
                )
                meta = ds[c].attrs["metadata"].metadata
                ds[c].attrs["metadata"] = dict(meta)
                for k, v in dict(meta).items():
                    if isinstance(v, np.ndarray):
                        ds[c].attrs["metadata"][k] = v.tolist()
        return ds

    def retrieve(
        self,
        source: str,
        variables: list[tuple[str, dict[str, Any]]],
        dates: datetime.date | str | pd.Timestamp | list[Any],
        unique_valid_datetimes: bool = False,
        instant_precip: bool = False,
        datatype: list[str] = ["analysis"],
        levels: int | list[int] = [80],
        step_hours: int | list[int] = 0,
        ensemble_members: int | list[int | None] | None = None,
    ) -> xr.Dataset:
        """
        Retrieve and process local grib data for given source, variables, and dates using meteodata-lab and earthkit data.

        Parameters
        ----------
        source : str
            Identifier of the data source.
        variables : list of tuple of (str, dict)
            List of variable definitions as tuples containing variable names and parameters.
        dates : list of datetime.date or datetime.date
            One or multiple dates for which data is to be retrieved.
        datatype : list of str, optional
            List of data types to retrieve, can be "forecast" or "analysis".
            Default is ["analysis"].
        levels : int or list of int, optional
            Model level(s) to retrieve. Default is [80].
        step_hours : int or list of int, optional
            Step hour(s) to retrieve. Default is 0.
        ensemble_members : int or list of int, optional
            Ensemble member(s) to retrieve. Default is None.

        Returns
        -------
        xarray.Dataset
            Merged dataset containing the processed local SEN data.
        """
        # check if eccodes is installed.
        # there are two things that can go wrong here:
        # 1. eccodes is not installed
        # 2. eccodes is installed but the library is not found
        try:
            import eccodes  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "The eccodes python bindings are required for reading GRIB files."
            ) from e
        except RuntimeError as e:
            raise RuntimeError(
                "eccodes library not found. Make sure the python bindings can find them."
            ) from e
        dates, variables = checktype(dates, variables)
        self.requested_variables = [v[0] for v in variables]
        step_hours = [step_hours] if isinstance(step_hours,
                                                int) else step_hours
        step_hours_sec = [
            pd.to_timedelta(s, unit="h").to_timedelta64() for s in step_hours
        ]

        datatypes = [
            self.type_mapping[typ]
            for typ in (datatype if isinstance(datatype, list) else [datatype])
        ]
        levels = [levels] if isinstance(levels, int) else levels
        self.levels = levels

        if not all(75 <= lev <= 80
                   for lev in levels) and not all(t in ["ANA", "FG"]
                                                  for t in datatypes):
            raise ValueError(
                "Only levels 75 to 80 are supported for forecast data.")
        ensemble_members = ([ensemble_members] if isinstance(
            ensemble_members, str | int | type(None)) else ensemble_members)
        self.ensembles = [self.ensemble_mapping[e] for e in ensemble_members]

        def get_all_files_from_date(
            date: datetime.date,
            t: str,
        ) -> list[pathlib.Path]:
            """
            Get list of files given the date and type of data requested. Can be adapted to different filesystems.
            """
            file = f"i{t[0].lower()}f"
            ensembles = [
                e if e is not None else ("000" if t == "FCST" else "det")
                for e in self.ensembles
            ]
            y = str(pd.to_datetime(date).year)[-2:]
            prefix = f"{self.prefix_mapping[source]}eff00" if source in self.prefix_mapping else ""
            specific_path = (self.path / source / f"{t}{y}" /
                             ensembles[0] if t != "FCST" else self.path /
                             source / f"{t}{y}")
            step_hours_str = [
                f"{int(s / np.timedelta64(1, 'h')):02}" for s in step_hours_sec
            ]
            if t == "FCST":
                patterns_list = [
                    f"{y}{date.strftime('%m%d')}*/grib/{prefix}{s}0000_{e}"
                    for s in step_hours_str for e in ensembles
                ]
            else:
                patterns_list = [f"{file}{date.strftime('%Y%m%d')}*"]
            patterns = set(patterns_list)
            all_files = sorted(
                chain.from_iterable(
                    specific_path.glob(pattern) for pattern in patterns))
            return all_files

        def handle_metadata(ds: xr.Dataset) -> xr.Dataset:
            md: dict[str, Any] = {str(v): {} for v in ds.data_vars}
            for v in ds.data_vars:
                if "metadata" in ds[v].attrs:
                    for key in ds[v].attrs["metadata"].metadata.keys():
                        try:
                            value = ds[v].attrs["metadata"].metadata.get(key)
                            md[str(v)][key] = value
                        except KeyError:
                            pass
                if "parameter" in ds[v].attrs:
                    md[str(v)].update({
                        str(k): v
                        for k, v in ds[v].attrs["parameter"].items()
                    })
                ds[v].attrs = md[str(v)]
            global_md = {}
            if "metadata" in ds.attrs:
                for key in ds.attrs["metadata"].metadata.keys():
                    try:
                        value = ds.attrs["metadata"].metadata.get(key)
                        global_md[key] = value
                    except KeyError:
                        pass
            ds.attrs = global_md
            return ds

        def open_and_process_data(all_paths: list[pathlib.Path]) -> xr.Dataset:
            try:
                fds = data_source.FileDataSource(
                    datafiles=[str(p) for p in all_paths])
                vars_on_vertical_levels = ["U", "V", "T", "QV", "P"]
                non_vert_params = list(
                    set(self.requested_variables).difference(
                        set(vars_on_vertical_levels)))
                dic = {}
                if len(non_vert_params):
                    dic = grib_decoder.load(fds, {"param": non_vert_params},
                                            geo_coords=_geo_coords)
                requested_vars_on_vertical_levels = list(
                    set(self.requested_variables).intersection(
                        set(vars_on_vertical_levels)))
                if len(requested_vars_on_vertical_levels) > 0:
                    dic.update(
                        grib_decoder.load(
                            fds,
                            {
                                "param": requested_vars_on_vertical_levels,
                                "levelist": self.levels
                            },
                            geo_coords=_geo_coords,
                        ))
                for var, da in dic.items():
                    if "z" in da.dims and da.sizes["z"] == 1:
                        dic[var] = da.squeeze("z", drop=True)
                    elif "z" in da.dims and da.sizes["z"] > 1:
                        dic[var] = da.rename({"z": da.attrs["vcoord_type"]})
                    if "eps" in da.dims and da.sizes["eps"] == 1:
                        dic[var] = da.squeeze("eps", drop=True)
                ds = xr.merge([dic[p].rename(p) for p in dic])
            except ValueError as exc:
                raise ValueError("Could not retrieve data.") from exc
            name_mapping = {
                "ref_time": "forecast_reference_time",
                "lon": "longitude",
                "lat": "latitude"
            }
            ds = ds.rename({
                k: name_mapping[str(k)]
                for k in ds.coords if k in name_mapping
            })
            ds = self.handle_metadata(ds)
            return ds.unify_chunks()

        def get_data_for_type(t: str) -> list[xr.Dataset]:
            concat = []
            for date in dates:
                all_paths = get_all_files_from_date(date, t)
                if all_paths:
                    new_data = open_and_process_data(all_paths)
                    if new_data is not None:
                        concat.append(new_data.drop_duplicates(...))
            return concat

        results = []
        for t in datatypes:
            results.extend(get_data_for_type(t))

        if results and len(results) > 1:
            ds = xr.merge(results, compat="override").drop_duplicates(...)
        elif results and len(results) == 1:
            ds = results[0]
            return ds
        raise RuntimeError("No results found for the given parameters.")

class NWPRetrieverFDB(FDBRetriever):
    """
    Retriever for NWP data utilizing the FDB system.

    This class, inheriting from FDBRetriever, is used for retrieving numerical weather prediction
    data from FDB sources.
    """

    def __init__(self) -> None:
        """
        Initialize the NWPRetrieverFDB instance.

        Configures origin coordinates and CRS, sets metadata fields, sources, and variables.
        """
        self.origin_lon = 10
        self.origin_lat = 47
        self.crs = (
            f"+proj=ob_tran +o_proj=longlat +lon_0={-180 + self.origin_lon} +o_lon_p=-180"
            f" +o_lat_p={90 + self.origin_lat}"
        ) # rotated lat-lon
        sources = (
            "COSMO-1E",
            "COSMO-2E",
            "KENDA-1",
            "ICON-CH1-EPS",
            "ICON-CH2-EPS",
            "KENDA-CH1",
        )
        variables = nwp_dic
        super().__init__(sources, variables)

    def retrieve(
        self,
        source: str,
        variables: list[tuple[str, dict]],
        dates: datetime.date | str | pd.Timestamp | list[Any],
        datatype: str = "analysis",
        ensemble_members: list[int] | int | None = 0,
    ) -> xr.Dataset:
        """
        Retrieve NWP data from FDB for given source, variables, and dates.

        Parameters
        ----------
        source : str
            Source identifier.
        variables : list of tuple of (str, dict)
            List of variable definitions.
        dates : list of datetime.date or datetime.date
            Date or list of dates.
        datatype : str, optional
            Type of data retrieval (default is "analysis").
        ensemble_members : int or list of int, optional
            The ensemble member number for the forecast retrieval. Defaults to 0.

        Returns
        -------
        xarray.Dataset
            Retrieved dataset with the forecast_reference_time.
        """
        dates, variables = checktype(dates, variables)
        return super().retrieve(
            source,
            variables,
            dates,
            datatype=datatype,
            ensemble_members=ensemble_members,
        )
