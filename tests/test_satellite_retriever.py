import pandas as pd
import pytest

from weathermart.retrievers.satellite import SatelliteRetriever
from weathermart.variable_naming import get_variables

seviri_variables = [
    "VIS006",
    "IR_039",
    "IR_108",
    "HRV",
    "IR_097",
    "WV_062",
    "IR_087",
    "IR_016",
    "VIS008",
    "IR_134",
    "WV_073",
    "IR_120",
]
cmsaf_variables = ["CLCT"]


def test_satellite_retriever_init():
    sr = SatelliteRetriever()

    assert sr.eumetsat_retriever.sources == ("SATELLITE",)
    assert list(sr.eumetsat_retriever.variables.keys()) == seviri_variables
    assert sr.eumetsat_retriever.crs == "epsg:4326"

    assert set(list(sr.variables.keys())) == set(seviri_variables + list(get_variables().keys()))


def test_satellite_retriever_wrong_database():
    sr = SatelliteRetriever()
    with pytest.raises(ValueError):
        sr.retrieve(
            source="some_source",
            variables="some_variable",
            dates=pd.date_range("2023-12-01", "2023-12-03"),
            through="wrong_database",
        )
