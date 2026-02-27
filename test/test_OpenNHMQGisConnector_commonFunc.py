''' Tests for module common functions'''
import pytest
import pathlib

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
