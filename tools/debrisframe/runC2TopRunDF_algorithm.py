# -*- coding: utf-8 -*-

__author__ = "OpenNHM Team"
__date__ = "2026-03-01"
__copyright__ = "(C) 2026 by OpenNHM Team"

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"


from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterFolderDestination,
    QgsProcessingOutputVectorLayer,
    QgsProcessingOutputMultipleLayers,
)

class runC2TopRunDFAlgorithm(QgsProcessingAlgorithm):
    """
    This is the DebrisFrame Connection, i.e. the part running with QGis. For this
    connector to work, more installation is needed. See instructions at docs.avaframe.org
    """

    DEM = "DEM"
    RELPOINT = "RELPOINT"
    OUTPUT = "OUTPUT"
    FOLDEST = "FOLDEST"
    DATA_TYPE = "DATA_TYPE"

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

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.FOLDEST, self.tr("Destination folder")
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.RELPOINT,
                self.tr("Release point (only one is allowed)"),
                types=[QgsProcessing.TypeVectorPoint],
            )
        )

        self.addOutput(
            QgsProcessingOutputVectorLayer(
                self.OUTPUT,
                self.tr("Output layer"),
                QgsProcessing.TypeVectorAnyGeometry,
            )
        )

    def flags(self):
        return super().flags()

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # import debrisframe.version as gv
        from ... import OpenNHMQGisConnector_commonFunc as cF

        # feedback.pushInfo("DebrisFrame Version: " + gv.getVersion())

        targetADDTONAME = ""

        sourceDEM = self.parameterAsRasterLayer(parameters, self.DEM, context)
        if sourceDEM is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.DEM))

        sourceFOLDEST = self.parameterAsFile(parameters, self.FOLDEST, context)

        # create folder structure (targetDir is the tmp one)
        finalTargetDir, targetDir = cF.createFolderStructure(sourceFOLDEST)

        feedback.pushInfo(sourceDEM.source())

        # copy DEM
        cF.copyDEM(sourceDEM, targetDir)

        # extract coordinated from release point
        sourcePoint = self.parameterAsSource(parameters, self.RELPOINT, context)
        if sourcePoint and sourcePoint.featureCount() != 1:
            raise QgsProcessingException("Exactly one release point is required.")
        featurePoint = next(sourcePoint.getFeatures())
        geomPoint = featurePoint.geometry()
        point = geomPoint.asPoint()

        x = point.x()
        y = point.y()


        feedback.pushInfo("Starting the simulations")
        feedback.pushInfo("This might take a while")
        feedback.pushInfo("See console for progress")

        # Generate command and run via subprocess
        command = ["python", "-m", "debrisframe.runC2TopRunDF", str(targetDir), "-x", str(x), "-y", str(y)]
        cF.runAndCheck(command, self, feedback)

        feedback.pushInfo("Done, start loading the results")

        # Move input, log and output folders to finalTargetDir
        #cF.moveInputAndOutputFoldersToFinal(targetDir, finalTargetDir)

        try:
            topRunResultsLayer = cF.getC2TopRunDFResults(targetDir)
        except:
            raise QgsProcessingException(self.tr('Something went wrong with c2TopRunDF, please check log files'))
        #context = cF.addSingleLayerToContext(context, topRunResultsLayer, self.OUTPUT)
        context = cF.addLayersToContext(context, topRunResultsLayer, self.OUTPUT)

        feedback.pushInfo('\n---------------------------------')
        feedback.pushInfo('Done, find results and logs here:')
        feedback.pushInfo(str(targetDir.resolve()))
        feedback.pushInfo('---------------------------------\n')

        return {self.OUTPUT: topRunResultsLayer}


    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'c2TopRunDF'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('pyTopRunDF (c2)')

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
        hstring = 'Runs pyTopRunDF via module c2. \n\
                For more information go to (or use the help button below): \n\
                DebrisFrame Documentation: https://docs.debrisframe.org\n\
                Homepage: https://opennhm.org/\n'

        return self.tr(hstring)

    def helpUrl(self):
        return "in progress"

    def createInstance(self):
        return runC2TopRunDFAlgorithm()
