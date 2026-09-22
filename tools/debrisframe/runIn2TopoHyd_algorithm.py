# -*- coding: utf-8 -*-

__author__ = "OpenNHM Team"
__date__ = "2026-09-22"
__copyright__ = "(C) 2026 by OpenNHM Team"

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"


import pathlib
import shutil

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingOutputVectorLayer,
)


class runIn2TopoHydAlgorithm(QgsProcessingAlgorithm):
    """
    This is the DebrisFrame Connection, i.e. the part running with QGis. For this
    connector to work, more installation is needed. See instructions at docs.avaframe.org
    """

    DEM = 'DEM'
    XSECT = 'XSECT'
    LEVEE = 'LEVEE'
    HYDR = 'HYDR'
    FOLDEST = 'FOLDEST'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.DEM, self.tr("DEM layer")
            )
        )

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.XSECT,
            self.tr('Release line, exactly two points - start and ending point (only one file is allowed)'),
            types=[QgsProcessing.TypeVectorLine]
            ))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.LEVEE,
            self.tr('Levee points, two points - left and right bank (only one file is allowed)'),
            types=[QgsProcessing.TypeVectorPoint]
            ))

        self.addParameter(QgsProcessingParameterFile(
            self.HYDR,
            self.tr(
                'Hydrograph csv file, must contain the columns timestep (values in [s]) '
                'and discharge (values in [m³/s])'
            ),
            behavior=QgsProcessingParameterFile.File,
            fileFilter='CSV files (*.csv)',
        ))

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.FOLDEST, self.tr("Destination folder")
            )
        )

        self.addOutput(QgsProcessingOutputVectorLayer(
            self.OUTPUT,
            self.tr("Cross section cells"),
            QgsProcessing.TypeVectorPoint))

    def flags(self):
        return super().flags()

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        from ... import OpenNHMQGisConnector_commonFunc as cF

        sourceDEM = self.parameterAsRasterLayer(parameters, self.DEM, context)
        if sourceDEM is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.DEM))

        sourceXSECT = self.parameterAsVectorLayer(parameters, self.XSECT, context)
        if sourceXSECT is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.XSECT))

        sourceLEVEE = self.parameterAsVectorLayer(parameters, self.LEVEE, context)
        if sourceLEVEE is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.LEVEE))

        sourceHYDR = self.parameterAsFile(parameters, self.HYDR, context)
        if not sourceHYDR:
            raise QgsProcessingException(self.tr("A hydrograph csv file is required."))

        sourceFOLDEST = self.parameterAsFile(parameters, self.FOLDEST, context)

        # release line must consist of exactly one feature with two points
        if sourceXSECT.featureCount() != 1:
            raise QgsProcessingException(self.tr("Release line must consist of exactly one feature."))
        featureLine = next(sourceXSECT.getFeatures())
        geometry = featureLine.geometry()
        if geometry.isEmpty() or geometry.constGet().nCoordinates() != 2:
            raise QgsProcessingException(self.tr("Release line must consist of exactly two points."))

        # create folder structure (targetDir is the tmp one)
        finalTargetDir, targetDir = cF.createFolderStructure(sourceFOLDEST)

        feedback.pushInfo(sourceDEM.source())

        # copy DEM
        cF.copyDEM(sourceDEM, targetDir)

        # create the input folders in2TopoHyd expects
        xsectDir = targetDir / "Inputs" / "XSECT"
        leveeDir = targetDir / "Inputs" / "LEVEE"
        hydrDir = targetDir / "Inputs" / "HYDR"
        for directory in (xsectDir, leveeDir, hydrDir):
            directory.mkdir(parents=True, exist_ok=True)

        # copy release line, levee points and hydrograph
        cF.copyShp(sourceXSECT.source(), xsectDir)
        cF.copyShp(sourceLEVEE.source(), leveeDir)
        shutil.copy(sourceHYDR, hydrDir / pathlib.Path(sourceHYDR).name)

        feedback.pushInfo("Starting the simulation")
        feedback.pushInfo("This might take a while")
        feedback.pushInfo("See console for progress")

        # Generate command and run via runAndCheck
        command = ["python", "-m", "debrisframe.runIn2TopoHyd", str(targetDir)]
        cF.runAndCheck(command, self, feedback)

        feedback.pushInfo("Done, start loading the results")

        # Move input, log and output folders to finalTargetDir
        cF.moveInputAndOutputFoldersToFinal(targetDir, finalTargetDir)

        try:
            results = cF.getIn2TopoHydResults(finalTargetDir, sourceDEM)
        except Exception as err:
            raise QgsProcessingException(
                f"{self.tr('Something went wrong with in2TopoHyd, please check log files')}\n{err}"
            )

        cellsLayer = results["crossSectionCells"]
        if cellsLayer is not None:
            context = cF.addSingleLayerToContext(context, cellsLayer, self.OUTPUT)

        if results["initCondHyd"]:
            feedback.pushInfo("Initial conditions written to:")
            feedback.pushInfo(results["initCondHyd"])
        if results["plots"]:
            feedback.pushInfo("Plots:")
            for plot in results["plots"]:
                feedback.pushInfo(plot)

        feedback.pushInfo('\n---------------------------------')
        feedback.pushInfo('Done, find results and logs here:')
        feedback.pushInfo(str(finalTargetDir.resolve()))
        feedback.pushInfo('---------------------------------\n')

        return {self.OUTPUT: cellsLayer}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'in2topohyd'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Hydrograph Starting Condition (in2TopoHyd)')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "DebrisFrame_Experimental"

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def shortHelpString(self) -> str:
        hstring = 'Computes the initial conditions at a release line (for debris flows) via module in2TopoHyd. \n\
                Requires a DEM, a release line (two points), levee points and a hydrograph csv. \n\
                The resulting initCondHyd.csv can be used as time dependent release input for c1TIF. \n\
                For more information go to (or use the help button below): \n\
                DebrisFrame Documentation: https://docs.debrisframe.org\n\
                Homepage: https://opennhm.org/\n'

        return self.tr(hstring)

    def helpUrl(self):
        return "in progress"

    def createInstance(self):
        return runIn2TopoHydAlgorithm()
