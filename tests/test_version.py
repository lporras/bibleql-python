import re
from importlib.metadata import version

import bibleql


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", bibleql.__version__)


def test_version_matches_installed_package_metadata():
    # pyproject.toml reads the version from _version.py; this checks the two stay wired together
    # without hard-coding a number that would need editing on every release.
    assert bibleql.__version__ == version("bibleql")
