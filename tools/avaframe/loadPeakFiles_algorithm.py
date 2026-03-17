# -*- coding: utf-8 -*-

__author__ = "AvaFrame Team"
__date__ = "2026"
__copyright__ = "(C) 2026 by AvaFrame Team"

__revision__ = "$Format:%H$"

import pathlib

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsRasterLayer,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterEnum,
    QgsProcessingOutputMultipleLayers,
)


PARAM_TYPES = ["ppr", "pft", "pfv", "timeInfo"]


class loadPeakFilesAlgorithm(QgsProcessingAlgorithm):
    """
    Scans a peak files directory, filters by selected result types,
    loads matching rasters and applies QML styles where available.
    """

    PEAKDIR = "PEAKDIR"
    RESTYPES = "RESTYPES"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PEAKDIR,
                self.tr("Avalanche directory"),
                behavior=QgsProcessingParameterFile.Folder,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.RESTYPES,
                self.tr("Result types to load"),
                options=PARAM_TYPES,
                allowMultiple=True,
                defaultValue=[0, 1, 2],
            )
        )

        self.addOutput(
            QgsProcessingOutputMultipleLayers(
                self.OUTPUT,
                self.tr("Loaded peak layers"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        import pandas as pd
        from avaframe.in3Utils import fileHandlerUtils as fU
        from ... import OpenNHMQGisConnector_commonFunc as cF

        avaDir = pathlib.Path(self.parameterAsFile(parameters, self.PEAKDIR, context))
        if not avaDir.is_dir():
            raise QgsProcessingException(self.tr(f"Directory does not exist: {avaDir}"))

        selectedIndices = self.parameterAsEnums(parameters, self.RESTYPES, context)
        selectedTypes = [PARAM_TYPES[i] for i in selectedIndices]

        feedback.pushInfo(f"Scanning: {avaDir}")
        feedback.pushInfo(f"Selected types: {', '.join(selectedTypes)}")

        # Find all peakFiles/ dirs, excluding timeSteps/ subdirectories
        peakDirs = [p for p in avaDir.rglob("peakFiles") if p.is_dir() and "timeSteps" not in p.parts]

        if not peakDirs:
            feedback.pushInfo("No peakFiles directories found.")
            return {self.OUTPUT: []}

        frames = []
        for peakDir in peakDirs:
            feedback.pushInfo(f"Found: {peakDir}")
            df = fU.makeSimDF(peakDir)
            if not df.empty:
                frames.append(df)

        if not frames:
            feedback.pushInfo("No peak files found in directory.")
            return {self.OUTPUT: []}

        allResults = pd.concat(frames, ignore_index=True)

        filtered = allResults[allResults["resType"].isin(selectedTypes)]

        if filtered.empty:
            feedback.pushInfo("No files matched the selected result types.")
            return {self.OUTPUT: []}

        feedback.pushInfo(f"Found {len(filtered)} matching file(s).")

        # QGisStyles lives at the repo root, two levels above tools/avaframe/
        scriptDir = pathlib.Path(__file__).parent.parent.parent
        qmls = {
            "ppr": str(scriptDir / "QGisStyles" / "ppr.qml"),
            "pft": str(scriptDir / "QGisStyles" / "pft.qml"),
            "pfd": str(scriptDir / "QGisStyles" / "pft.qml"),
            "pfv": str(scriptDir / "QGisStyles" / "pfv.qml"),
            "PR": str(scriptDir / "QGisStyles" / "ppr.qml"),
            "FV": str(scriptDir / "QGisStyles" / "pfv.qml"),
            "FT": str(scriptDir / "QGisStyles" / "pft.qml"),
            "timeInfo": str(scriptDir / "QGisStyles" / "timeInfo.qml"),
        }

        allRasterLayers = []
        for _, row in filtered.iterrows():
            rstLayer = QgsRasterLayer(str(row["files"]), row["names"])
            if not rstLayer.isValid():
                feedback.pushInfo(f"Skipping invalid layer: {row['files']}")
                continue
            qml = qmls.get(row["resType"])
            if qml:
                rstLayer.loadNamedStyle(qml)
            allRasterLayers.append(rstLayer)

        context = cF.addLayersToContext(context, allRasterLayers, self.OUTPUT)

        feedback.pushInfo(f"Loaded {len(allRasterLayers)} layer(s).")
        return {self.OUTPUT: allRasterLayers}

    def name(self):
        return "loadpeakfiles"

    def displayName(self):
        return self.tr("Load peak files from directory")

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return "AvaFrame_Experimental"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def shortHelpString(self) -> str:
        hstring = (
            "Scans an AvaFrame avalanche directory for peakFiles folders and loads the selected "
            "result types (ppr, pft, pfv, timeInfo) as raster layers with styles applied "
            "where available. Timestep files are excluded.\n\n"
            "Point the directory input at the avalanche directory root, e.g.:\n"
            "avaKot\n\n"
            "AvaFrame Documentation: https://docs.avaframe.org\n"
            "Homepage: https://avaframe.org\n"
        )
        return self.tr(hstring)

    def helpUrl(self):
        return "https://docs.avaframe.org/en/latest/connector.html"

    def icon(self):
        from qgis.PyQt.QtGui import QIcon
        icon_path = pathlib.Path(__file__).parent.parent.parent / "icons" / "icon.png"
        return QIcon(str(icon_path))

    def createInstance(self):
        return loadPeakFilesAlgorithm()
