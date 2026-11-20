''' Tests for module common functions'''
import pytest
import pathlib

from qgis.core import QgsProcessingException

# Local imports
from .. import OpenNHMQGisConnector_commonFunc as cF 


def test_getSHPParts(tmp_path):
    """ test getSHPParts"""

    inputDir = pathlib.Path(__file__).parent / 'data' / 'avaSlide' / 'Inputs'
    shpParts = cF.getSHPParts(inputDir / 'REL' / 'slideRelease.shp')
    extensions = list()
    for ele in shpParts:
        extensions.append(ele.suffix)

    assert len(extensions) == 5
    assert '.prj' in extensions
    assert '.cpg' in extensions
    assert '.shx' in extensions
    assert '.dbf' in extensions
    assert '.shp' in extensions


class DummyFeedback:
    """Minimal feedback stub recording pushed info messages."""

    def __init__(self):
        self.messages = []

    def pushInfo(self, msg):
        self.messages.append(msg)


def test_writeDefaultModuleIni(tmp_path):
    """The default ini of an importable module is copied to the destination."""

    feedback = DummyFeedback()
    dest = tmp_path / "com1DFACfg.ini"

    result = cF.writeDefaultModuleIni(
        "avaframe.com1DFA", "com1DFACfg.ini", dest, feedback, "com1DFA"
    )

    assert result == dest
    assert dest.is_file()
    assert dest.stat().st_size > 0
    assert "[" in dest.read_text()
    assert any("com1DFA" in msg for msg in feedback.messages)


def test_writeDefaultModuleIniMissingConfig(tmp_path):
    """A config missing next to the module raises a clear processing exception."""

    with pytest.raises(QgsProcessingException, match="Default config not found"):
        cF.writeDefaultModuleIni(
            "avaframe.com1DFA", "doesNotExistCfg.ini", tmp_path / "x.ini", DummyFeedback(), "com1DFA"
        )


def test_copyCfgFileCreatesAndOverwrites(tmp_path):
    """copyCfgFile creates Inputs/CFGs and overwrites an existing file."""

    src = tmp_path / "src.ini"
    src.write_text("[SECTION]\nvalue = 1\n")
    targetDir = tmp_path / "debris"

    cF.copyCfgFile(src, targetDir, "com1DFACfg.ini")
    dest = targetDir / "Inputs" / "CFGs" / "com1DFACfg.ini"
    assert dest.is_file()
    assert "value = 1" in dest.read_text()

    src.write_text("[SECTION]\nvalue = 2\n")
    cF.copyCfgFile(src, targetDir, "com1DFACfg.ini")
    assert "value = 2" in dest.read_text()
