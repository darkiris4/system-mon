import re

from systemmon import __version__


def test_version_is_semver_shaped():
    assert re.match(r"^\d+\.\d+\.\d+$", __version__)
