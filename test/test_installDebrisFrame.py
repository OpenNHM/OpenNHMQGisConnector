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
PIP = [PYTHON, "-m", "pip", "install", "--user", "--upgrade", "--pre"]
AVAFRAME_CMD = PIP + ["avaframe"]
DEBRISFRAME_CMD = PIP + ["debrisframe"]


@pytest.mark.parametrize(
    "installedVersion, needsConfirmation, expectedCommands",
    [
        (None, False, [AVAFRAME_CMD, DEBRISFRAME_CMD]),
        ("2.1", True, [AVAFRAME_CMD, DEBRISFRAME_CMD]),
        ("2.2b0", True, [AVAFRAME_CMD, DEBRISFRAME_CMD]),
        ("2.2b1", False, [DEBRISFRAME_CMD]),
        ("2.2.0", False, [DEBRISFRAME_CMD]),
        ("2.3", False, [DEBRISFRAME_CMD]),
    ],
)
def test_buildDebrisFrameInstallPlan(installedVersion, needsConfirmation, expectedCommands):
    needsConfirm, commands = buildDebrisFrameInstallPlan(PYTHON, installedVersion)
    assert needsConfirm is needsConfirmation
    assert commands == expectedCommands


def test_buildDebrisFrameInstallPlan_invalid_version_requires_confirmation():
    needsConfirm, commands = buildDebrisFrameInstallPlan(PYTHON, "not-a-version")
    assert needsConfirm is True
    assert commands == [AVAFRAME_CMD, DEBRISFRAME_CMD]


def test_getInstalledVersion_missing_distribution_returns_none():
    assert getInstalledVersion("avaframe-distribution-does-not-exist") is None
