from typing import Any

import pytest

from weathermart.provide import _format_kwarg


@pytest.mark.parametrize(
    "k,v,expected",
    [
        ("levels", [100, 200, 300], "level100to300"),
        ("levels", [500], "level500"),
        ("levels", 100, "level100"),
        ("step_hours", [3, 6, 9], "step3to9"),
        ("step_hours", 12, "step12"),
        ("unique_valid_datetimes", True, "unique_valid_datetimes"),
        ("instant_precip", False, "instant_precip"),
        ("ensemble_members", 10, "ens10"),
        ("ensemble_members", [1], "ens1"),
        ("ensemble_members", [1, 2, 3], "ens1to3"),
        ("some_list", [1.1, 2.2], "11_22"),
        ("through", "eumetsat", "eumetsat"),
        ("through", ["a", "b"], "a_b"),
        ("key", "v.a.lue", "value"),
        ("use_limitation", 30, "limitation30"),
        ("use_limitation", [30], "limitation30"),
        ("use_limitation", [20], None),  # 20 is the default and should not be included
        ("use_limitation", 20, None),
    ],
)
def test_format_kwarg(k: str, v: Any, expected: str):
    assert _format_kwarg(k, v) == expected


def test_invalidchar_format_kwarg():
    with pytest.raises(ValueError):
        _format_kwarg("path", "a/b/c")


def test_level_notsorted():
    with pytest.raises(ValueError):
        _format_kwarg("levels", [100, 50, 300])


def test_duplicates():
    with pytest.raises(ValueError):
        _format_kwarg("levels", [100, 100, 300])
    with pytest.raises(ValueError):
        _format_kwarg("levels", [100, 100])


@pytest.mark.parametrize(
    "k,v",
    [
        ("levels", []),
        # TODO: add more cases for empty values (e.g. v=[None])
    ],
)
def test_empty_format_kwarg(k: str, v: Any):
    with pytest.raises(ValueError):
        result = _format_kwarg(k, v)
        print(result)
