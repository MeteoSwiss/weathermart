from pathlib import Path
from typing import Any

import pandas as pd


def get_variables() -> dict[str, Any]:
    """
    Retrieve variable definitions from the local csv file.
    Has to be updated for new users, so far it is generated
    from an internal MeteoSwiss pipeline.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing variable definitions.
    """
    variable_file = Path(__file__).parent / "variable_metadata.csv"
    return pd.read_csv(variable_file)
