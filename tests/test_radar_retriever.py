import pytest

from weathermart.retrievers.radar import read_radar_file_or_raise


def test_read_radar_file_or_raise():
    with pytest.raises(RuntimeError):
        read_radar_file_or_raise("fake_file")
