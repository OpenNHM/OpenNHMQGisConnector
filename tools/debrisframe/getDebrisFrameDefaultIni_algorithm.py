# -*- coding: utf-8 -*-

__author__ = "OpenNHM Team"
__date__ = "2026-09-28"
__copyright__ = "(C) 2026 by OpenNHM Team"

__revision__ = "$Format:%H$"

import pathlib

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFileDestination,
)


class getDebrisFrameDefaultIniAlgorithm(QgsProcessingAlgorithm):
    """
    Extracts the default configuration ini file for a given DebrisFrame module
    and writes it to the specified destination.
    """

    # To add a new module: append a tuple (label, importPath, cfgFileName)
    # label:      shown in the dropdown
    # importPath: DebrisFrame submodule to import for locating the cfg file
    # cfgFileName: name of the cfg file within that module's directory
    MODULES = [
        ("c1TIF", "debrisframe.c1TIF", "c1TIFCfg.ini"),
        ("in2TopoHyd", "debrisframe.in2TopoHyd", "in2TopoHydCfg.ini"),
    ]

    MODULE = "MODULE"
    OUTPUT_FILE = "OUTPUT_FILE"

    def initAlgorithm(self, config):
        """Define the module selection and the destination file parameters."""
        self.addParameter(
            QgsProcessingParameterEnum(
                self.MODULE,
                self.tr("Module"),
                options=[m[0] for m in self.MODULES],
                defaultValue=0,
                allowMultiple=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_FILE,
                self.tr("Destination file"),
                fileFilter="INI files (*.ini)",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Write the default ini file of the selected module to the destination file."""
        from ... import OpenNHMQGisConnector_commonFunc as cF

        moduleIdx = self.parameterAsEnum(parameters, self.MODULE, context)
        label, importPath, cfgName = self.MODULES[moduleIdx]

        destFile = self.parameterAsFileOutput(parameters, self.OUTPUT_FILE, context)

        cF.writeDefaultModuleIni(importPath, cfgName, destFile, feedback, label)

        return {self.OUTPUT_FILE: destFile}

    def name(self):
        """Return the unique, non-localised algorithm name."""
        return "getdebrisframedefaultini"

    def displayName(self):
        """Return the user visible algorithm name."""
        return self.tr("Get default DebrisFrame module ini")

    def group(self):
        """Return the localised group name."""
        return self.tr(self.groupId())

    def groupId(self):
        """Return the unique, non-localised group id."""
        return "DebrisFrame_Experimental"

    def tr(self, string):
        """Translate a string in the Processing context."""
        return QCoreApplication.translate("Processing", string)

    def shortHelpString(self) -> str:
        """Return the help text shown in the algorithm dialog."""
        hstring = "Extracts the default configuration ini file for the selected DebrisFrame module. \n\
                The file can then be edited and supplied as the expert configuration file \n\
                when running the corresponding simulation tool. \n\
                For more information go to (or use the help button below): \n\
                DebrisFrame Documentation: https://docs.debrisframe.org\n\
                Homepage: https://opennhm.org/\n"
        return self.tr(hstring)

    def helpUrl(self):
        """Return the help url, empty as no dedicated page exists yet."""
        return ""

    def icon(self):
        """Return the plugin icon."""
        icon_path = pathlib.Path(__file__).parent.parent.parent / "icons" / "icon.png"
        return QIcon(str(icon_path))

    def createInstance(self):
        """Return a new instance of this algorithm."""
        return getDebrisFrameDefaultIniAlgorithm()
