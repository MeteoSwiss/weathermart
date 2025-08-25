import tempfile

import numpy as np
import pytest
import xarray as xr
from test_retrievers import MockRetriever

from weathermart.provide import CacheRetriever
from weathermart.provide import DataProvider


def test_cacheprovider() -> None:
    with tempfile.TemporaryDirectory() as tmpdirname:
        cache = CacheRetriever(tmpdirname)
        m = MockRetriever()
        DataProvider(cache, [m])


def test_cacheprovider_notexist() -> None:
    with tempfile.TemporaryDirectory() as tmpdirname:
        with pytest.raises(FileNotFoundError):
            CacheRetriever(f"{tmpdirname}/nonexistent")


def test_cacheprovider_notdir() -> None:
    with tempfile.NamedTemporaryFile() as tmpfile:
        with pytest.raises(NotADirectoryError):
            CacheRetriever(tmpfile.name)


def test_cache() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheRetriever(tmpdir)
        mock = MockRetriever()
        provider = DataProvider(cache, [mock])
        date = ["2024-01-01"]
        provider.provide_from_config({"FAKE": ["TOT_PREC", "T2M"], "dates": date})
        # check if data is actually there
        ds = xr.open_zarr(f"{tmpdir}/fake/20240101")
        # check if data is the expected shape
        assert ds["T2M"].shape == (144, 2)
        assert ds["TOT_PREC"].shape == (144, 2)
        values_first = ds["T2M"].values
        # check if data is the same if it is read again
        cache = CacheRetriever(tmpdir)
        mock = MockRetriever()
        provider = DataProvider(cache, [mock])
        provider.provide_from_config({"FAKE": ["TOT_PREC", "T2M"], "dates": date})
        ds = xr.open_zarr(f"{tmpdir}/fake/20240101")
        values_second = ds["T2M"].values
        assert np.all(values_first == values_second)


def test_append():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheRetriever(tmpdir)
        mock = MockRetriever()
        provider = DataProvider(cache, [mock])
        date = ["2024-01-01"]
        provider.provide_from_config({"FAKE": ["TOT_PREC"], "dates": date})
        provider.provide_from_config({"FAKE": ["T2M"], "dates": date})
        # check if data is actually there
        ds = xr.open_zarr(f"{tmpdir}/fake/20240101")
        # check if data is the expected shape
        assert ds["T2M"].shape == (144, 2)
        assert ds["TOT_PREC"].shape == (144, 2)
