"""Tests for the DebrisFrame install plan and version helpers."""

import pathlib
import sys

import pytest

# Make the plugin importable as "OpenNHMQGisConnector"
PLUGIN_DIR = pathlib.Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from OpenNHMQGisConnector.OpenNHMQGisConnector_provider import (  # noqa: E402
    buildDebrisFrameInstallPlan,
    getInstalledVersion,
)

PYTHON = "python"
PIP = [PYTHON, "-m", "pip", "install", "--user", "--upgrade"]
AVAFRAME_CMD = PIP + ["avaframe>=2.2"]
DEBRISFRAME_CMD = PIP + ["debrisframe>=0.1a1"]


@pytest.mark.parametrize(
    "installedVersion, expectedCommands",
    [
        (None, [AVAFRAME_CMD, DEBRISFRAME_CMD]),
        ("2.1", [AVAFRAME_CMD, DEBRISFRAME_CMD]),
        ("2.2b1", [AVAFRAME_CMD, DEBRISFRAME_CMD]),
        ("2.2", [DEBRISFRAME_CMD]),
        ("2.3", [DEBRISFRAME_CMD]),
        ("not-a-version", [AVAFRAME_CMD, DEBRISFRAME_CMD]),
    ],
)
def test_buildDebrisFrameInstallPlan(installedVersion, expectedCommands):
    assert buildDebrisFrameInstallPlan(PYTHON, installedVersion) == expectedCommands


def test_getInstalledVersionMissingDistributionReturnsNone():
    assert getInstalledVersion("avaframe-distribution-does-not-exist") is None
