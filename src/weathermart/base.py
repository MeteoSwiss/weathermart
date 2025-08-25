"""
Module: base
Provides utility functions and classes for the data provider.
"""

import datetime
import inspect
from abc import ABC
from abc import abstractmethod
from typing import Any

import dask
import pandas as pd
import xarray as xr

from weathermart.variable_naming import get_variables

variables_metadata = get_variables()


class BaseRetriever(ABC):
    """
    Protocol for Data Retrievers.

    This class defines the interface for data retriever implementations which must adhere
    to this protocol.
    """

    sources: tuple[str, ...]
    """Supported source identifiers. Can be model name for NWP data, e.g. "ICON-CH1-EPS"
    or "COSMO-1E" and it will be used for retrieval via gridefix or local file systems.
    Can also be a generic name for the measurement data, e.g. "SATELLITE" or "RADAR",
    and it will not be used for retrieval but will define the folder name.
    """
    variables: dict[str, list[str]]
    """Variable mapping for each source. User provided variables should match COSMO/ICON
    convention
    (https://meteoswiss.atlassian.net/wiki/spaces/~atr/pages/23987112/2.2+COSMO-1E+Operational+Products).
    The mapping and metadata for each variable are defined in this page
    (https://meteoswiss.atlassian.net/wiki/spaces/Nowcasting/pages/370049179/Data+model+for+output+parameters)
    and# downloaded from Confluence in the variable_naming module. Metadata for each
    variable is stored in the retrieved xarray Dataset.
    """
    crs: str | dict[str, str]
    """Coordinate reference system for the data. Saved as part of the dataset metadata.
    Can be a grid mapping/proj str, or "epsg:N" where N is an EPSG code. Anything
    readable by pyproj is accepted. If the retriever is a composition of other 
    retrievers, the crs can be a dictionary.
    """
    _ignored_args: list[str] = [
        "source",
        "variables",
        "dates",
        "rename",
        "kwargs",
    ]
    """Arguments to ignore when checking for valid kwargs"""
    subretrievers: tuple["BaseRetriever", ...] = ()
    """Sub-retrievers for data retrieval. This is used for composite retrievers that
    combine multiple retrievers. For example, a retriever that retrieves data from
    multiple sources or a retriever that retrieves data from multiple APIs.
    """
    priority: int = 0
    """Priority of the retriever. Higher priority retrievers are preferred when multiple
    retrievers support the same source.
    """

    @abstractmethod
    def retrieve(
        self,
        source: str,
        variables: list[tuple[str, dict]],
        dates: datetime.date | str | pd.Timestamp | list[Any],
    ) -> xr.Dataset:
        """
        Retrieve data for the specified source, variables, and dates.
        Additional kwargs can be passed to retrievers, depending on the API/local file system used.
        For example, EUMETSAT API and NASADEM require a "bbox" parameter to specify the bounding box for the data
        retrieval.
        NWP data can be filtered by ensemble member (arg. "ensemble_members") and forecast step (arg. "step_hour").
        Station data can be filtered by poi (arg. station_id).
        Satellite, radar and NWP data can be retrieved with different APIs: the user can define which one to use, with
        the argument "through" (gridefix, EUMETSAT, balfrin).

        Parameters
        ----------
        source : str
            Source identifier for the data retrieval.
        variables : list of tuple (str, dict)
            List of variable definitions as tuples containing variable names and additional parameters.
        dates : list of datetime.date
            List of datetimes for which to retrieve the data.

        Returns
        -------
        xr.Dataset
            Dataset containing the retrieved data.
            If NWP data, the dataset might be indexed by realization (ensemble members), in addition to
            forecast_reference_time and lead_time.
            Spatial coordinates can be 1D (station, cell) or 2D (x, y) depending on the source.
            Observations, including analysis data, are only indexed by time and the
            spatial coordinates.
            The dataset contains metadata for each variable, as defined in the variable_naming module.
            No specific reprojection to a given crs (coordinate reference system) is performed, but the origin crs is
            saved as part of the dataset metadata and when possible, the user should be able to select a domain of
            interest.
        """
        raise NotImplementedError

    def get_kwargs(self) -> list[str]:
        """
        Get the list of keyword arguments for the retrieve method.


        Returns
        -------
        list of str
            List of keyword arguments that can be passed to the retrieve method.
            This includes the arguments defined in the retrieve method and any additional arguments
            from subretrievers. Duplicates are removed.
        """
        kwarg_keys = [
            x for x in list(inspect.signature(self.retrieve).parameters.keys()) if x not in self._ignored_args
        ]
        if self.subretrievers:
            if isinstance(self.subretrievers, dict):
                tmp = self.subretrievers.values()
            else:
                tmp = self.subretrievers
            for subretriever in tmp:
                subretriever_kwargs = subretriever.get_kwargs()
                if subretriever_kwargs is not None:
                    kwarg_keys.extend(subretriever_kwargs)
        # Remove duplicates
        kwarg_keys = list(set(kwarg_keys))
        return kwarg_keys

    def validate_kwargs(self, kwargs: list[str]) -> None:
        """
        Checks if all provided kwargs are valid for this retriever.

        Parameters
        ----------
        kwargs : list of str
            List of keyword arguments to validate.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If any kwarg is not implemented for this retriever.
        """

        kwarg_keys = self.get_kwargs()
        for kwarg in kwargs:
            if kwarg not in kwarg_keys:
                raise ValueError(f"Kwarg {kwarg} not implemented for {self} retriever. Options are {kwarg_keys}.")


dask.config.set({"array.chunk-size": "256MiB"})


def checktype(
    dates: datetime.date | str | pd.Timestamp | list[Any],
    variables: str | list[Any],
) -> tuple[list[pd.Timestamp], list[tuple[str, dict]]]:
    """
    Process and normalize input dates and variables.

    Parameters
    ----------
    dates : datetime.date, str, pd.Timestamp, or list
        Input date(s) to be normalized.
    variables : str or list
        Variable(s) to be normalized. If a single string is provided, it will be converted
        to a list of one tuple (variable, {}).
        If a list of strings is provided, each will be converted to a tuple.

    Returns
    -------
    tuple
        A tuple (dates, variables) where dates is a sorted list of timestamps and variables is a
        list of tuples (variable, {}).
    """
    if isinstance(dates, list):
        dates = sorted({pd.to_datetime(date) for date in dates})
    if isinstance(dates, datetime.date):
        dates = [dates]
    elif isinstance(dates, str):
        dates = [pd.to_datetime(dates)]
    if isinstance(dates, pd.Timestamp):
        dates = [dates]
    if isinstance(variables, str):
        variables = [(variables, {})]
    elif bool(variables) and isinstance(variables, list) and all(isinstance(elem, str) for elem in variables):
        variables = [(v, {}) for v in variables]
    return dates, variables


def merge_dicts_with_list_str(*dicts: dict[str, list[str]]) -> dict[str, list[str]]:
    """
    Merge multiple dictionaries whose values are lists of strings.

    For any keys that appear in more than one dictionary, the resulting list is the union
    of the lists with duplicates removed while preserving the order of first occurrence.

    Parameters
    ----------
    *dicts : dict
        Arbitrary number of dictionaries with list-of-string values.

    Returns
    -------
    dict
        A single dictionary with merged keys.
    """
    result: dict[str, list[Any]] = {}
    for d in dicts:
        for key, val in d.items():
            if key in result:
                # Merge lists preserving order and uniqueness.
                seen = set(result[key])
                result[key].extend(item for item in val if item not in seen)
            else:
                result[key] = val.copy()
    return result
