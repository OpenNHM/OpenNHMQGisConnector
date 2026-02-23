# -*- coding: utf-8 -*-

__author__ = "AvaFrame Team"
__date__ = "2026"
__copyright__ = "(C) 2026 by AvaFrame Team"

__revision__ = "$Format:%H$"

import pathlib
import shutil

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFileDestination,
)


class getDefaultModuleIniAlgorithm(QgsProcessingAlgorithm):
    """
    Extracts the default configuration ini file for a given AvaFrame module
    and writes it to the specified destination.
    """

    # To add a new module: append a tuple (label, importPath, cfgFileName)
    # label:      shown in the dropdown
    # importPath: avaframe submodule to import for locating the cfg file
    # cfgFileName: name of the cfg file within that module's directory
    MODULES = [
        ("com1DFA",           "com1DFA",           "com1DFACfg.ini"),
        ("com2AB",            "com2AB",             "com2ABCfg.ini"),
        ("com5SnowSlide",     "com5SnowSlide",      "com5SnowSlideCfg.ini"),
        ("com6RockAvalanche", "com6RockAvalanche",  "com6RockAvalancheCfg.ini"),
        ("com6Scarp",         "com6RockAvalanche",  "scarpCfg.ini"),
        ("com8MoTPSA",        "com8MoTPSA",         "com8MoTPSACfg.ini"),
        ("com9MoTVoellmy",    "com9MoTVoellmy",     "com9MoTVoellmyCfg.ini"),
    ]

    MODULE = "MODULE"
    OUTPUT_FILE = "OUTPUT_FILE"

    def initAlgorithm(self, config):
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
        import importlib

        moduleIdx = self.parameterAsEnum(parameters, self.MODULE, context)
        label, importPath, cfgName = self.MODULES[moduleIdx]

        mod = importlib.import_module(f"avaframe.{importPath}")
        cfgPath = pathlib.Path(mod.__file__).parent / cfgName

        if not cfgPath.is_file():
            raise QgsProcessingException(self.tr(f"Default config not found: {cfgPath}"))

        destFile = self.parameterAsFileOutput(parameters, self.OUTPUT_FILE, context)
        shutil.copy(cfgPath, destFile)

        feedback.pushInfo(f"Written default config for {label} to:")
        feedback.pushInfo(str(destFile))
        feedback.pushInfo("")
        feedback.pushInfo("======READ THIS====")
        feedback.pushInfo("Edit this file in a text editor and provide it in the")
        feedback.pushInfo("Advanced section of the corresponding module interface.")
        feedback.pushInfo("======READ THIS====")
        feedback.pushInfo("")

        return {self.OUTPUT_FILE: destFile}

    def name(self):
        return "getdefaultmoduleini"

    def displayName(self):
        return self.tr("Get default module ini")

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return "AvaFrame_Experimental"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def shortHelpString(self) -> str:
        hstring = "Extracts the default configuration ini file for the selected AvaFrame module. \n\
                The file can then be edited and supplied as the expert configuration file \n\
                when running the corresponding simulation tool. \n\
                For more information go to (or use the help button below): \n\
                AvaFrame Documentation: https://docs.avaframe.org\n\
                Homepage: https://avaframe.org\n"
        return self.tr(hstring)

    def helpUrl(self):
        return "https://docs.avaframe.org/en/latest/connector.html"

    def createInstance(self):
        return getDefaultModuleIniAlgorithm()
