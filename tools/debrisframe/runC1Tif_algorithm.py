# -*- coding: utf-8 -*-

__author__ = "OpenNHM Team"
__date__ = "2026-03-01"
__copyright__ = "(C) 2026 by OpenNHM Team"

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"


import pathlib

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingOutputVectorLayer,
    QgsProcessingOutputMultipleLayers,
)

class runC1TifAlgorithm(QgsProcessingAlgorithm):
    """
    This is the DebrisFrame Connection, i.e. the part running with QGis. For this
    connector to work, more installation is needed. See instructions at docs.avaframe.org
    """

    DEM = 'DEM'
    REL = 'REL'
    RELCSV = 'RELCSV'
    SECREL = 'SECREL'
    ENT = 'ENT'
    RES = 'RES'
    OUTPUT = 'OUTPUT'
    OUTPPR = 'OUTPPR'
    FOLDEST = 'FOLDEST'
    ADDTONAME = "ADDTONAME"
    SMALLAVA = 'SMALLAVA'
    DATA_TYPE = 'DATA_TYPE'

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

        self.addParameter(QgsProcessingParameterMultipleLayers(
            self.REL,
            self.tr('Release layer(s)'),
            layerType=QgsProcessing.TypeVectorAnyGeometry
            ))

        self.addParameter(QgsProcessingParameterFile(
            self.RELCSV,
            self.tr('Time dependent release values (csv file)'),
            optional=True,
            defaultValue="",
            behavior=QgsProcessingParameterFile.File,
            fileFilter='CSV files (*.csv)',
        ))


        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.FOLDEST, self.tr("Destination folder")
            )
        )

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.SECREL,
            self.tr('Secondary release layer (only one is allowed)'),
            optional=True,
            defaultValue="",
            types=[QgsProcessing.TypeVectorAnyGeometry]
        ))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.ENT,
            self.tr('Entrainment layer (only one is allowed)'),
            optional=True,
            defaultValue="",
            types=[QgsProcessing.TypeVectorAnyGeometry]
        ))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.RES,
            self.tr('Resistance layer (only one is allowed)'),
            optional=True,
            defaultValue="",
            types=[QgsProcessing.TypeVectorAnyGeometry]
        ))

        self.addOutput(
            QgsProcessingOutputVectorLayer(
                self.OUTPUT,
                self.tr("Output layer"),
                QgsProcessing.TypeVectorAnyGeometry,
            )
        )

        self.addOutput(QgsProcessingOutputMultipleLayers(
            self.OUTPPR,
        ))

    def flags(self):
        return super().flags()

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # import debrisframe.version as gv
        from avaframe.in3Utils import initializeProject as iP
        from ... import OpenNHMQGisConnector_commonFunc as cF

        # feedback.pushInfo("DebrisFrame Version: " + gv.getVersion())

        targetADDTONAME = ""

        sourceDEM = self.parameterAsRasterLayer(parameters, self.DEM, context)
        if sourceDEM is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.DEM))

        # Release files
        allREL = self.parameterAsLayerList(parameters, self.REL, context)
        if allREL is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.REL))

        relDict = {}
        if allREL:
            relDict = {lyr.source(): lyr for lyr in allREL}

        # Secondary release files
        sourceSecREL = self.parameterAsVectorLayer(parameters, self.SECREL, context)
        if sourceSecREL is not None:
            srInfo = '_sec' + pathlib.Path(sourceSecREL.source()).stem
            targetADDTONAME = targetADDTONAME + srInfo

        sourceRELCSV = self.parameterAsVectorLayer(parameters, self.RELCSV, context)

        sourceENT = self.parameterAsVectorLayer(parameters, self.ENT, context)

        sourceRES = self.parameterAsVectorLayer(parameters, self.RES, context)

        sourceFOLDEST = self.parameterAsFile(parameters, self.FOLDEST, context)

        # create folder structure (targetDir is the tmp one)
        targetDir = pathlib.Path(sourceFOLDEST)
        iP.initializeFolderStruct(targetDir, removeExisting=False)

        feedback.pushInfo(sourceDEM.source())

        # copy DEM
        cF.copyDEM(sourceDEM, targetDir)

        # copy all release shapefile parts
        cF.copyMultipleShp(relDict, targetDir / "Inputs" / "REL")

        if sourceSecREL is not None:
            cF.copyShp(sourceSecREL.source(), targetDir / 'Inputs' / 'SECREL')

        # copy all entrainment shapefile parts
        if sourceENT is not None:
            cF.copyShp(sourceENT.source(), targetDir / 'Inputs' / 'ENT')

        if sourceRELCSV is not None:
            cF.copyRaster(sourceRELCSV, targetDir / "Inputs" / "REL", "")

        # copy all resistance shapefile parts
        if sourceRES is not None:
            cF.copyShp(sourceRES.source(), targetDir / "Inputs" / "RES")

        feedback.pushInfo("Starting the simulations")
        feedback.pushInfo("This might take a while")
        feedback.pushInfo("See console for progress")

        # Generate command and run via subprocess
        command = ["python", "-m", "debrisframe.runC1Tif", str(targetDir)]
        cF.runAndCheck(command, self, feedback)

        feedback.pushInfo("Done, start loading the results")

        # Move input, log and output folders to finalTargetDir
        #cF.moveInputAndOutputFoldersToFinal(targetDir, finalTargetDir)

        # Get peakfiles to return to QGIS
        try:
            rasterResults = cF.getLatestPeak(targetDir)
        except:
            raise QgsProcessingException(self.tr('Something went wrong with c1Tif, please check log files'))

        allRasterLayers = cF.addStyleToCom1DFAResults(rasterResults)

        context = cF.addLayersToContext(context, allRasterLayers, self.OUTPPR)

        feedback.pushInfo('\n---------------------------------')
        feedback.pushInfo('Done, find results and logs here:')
        feedback.pushInfo(str(targetDir.resolve()))
        feedback.pushInfo('---------------------------------\n')

        return {self.OUTPUT: allRasterLayers}


    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'c1Tticknessintegrated'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Thickness integrated flow (c1)')

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
        hstring = 'Runs thickness integrated simulation (for debris flows) via module c1. \n\
                For more information go to (or use the help button below): \n\
                DebrisFrame Documentation: https://docs.debrisframe.org\n\
                Homepage: https://opennhm.org/\n'

        return self.tr(hstring)

    def helpUrl(self):
        return "in progress"

    def createInstance(self):
        return runC1TifAlgorithm()
