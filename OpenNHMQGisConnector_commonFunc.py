# -*- coding: utf-8 -*-
import pathlib
import shutil
import pandas as pd
import os
import time
from avaframe.in3Utils import fileHandlerUtils as fU
from avaframe.in3Utils import initializeProject as iP

from qgis.core import QgsProcessingException


def copyDEM(dem, targetDir):
    """copies the DEM to targetDir/Inputs

    Parameters
    -----------
    dem:
        qgis source of dem
    targetDir: string
        base avalanche target directory
    """
    sourceDEMPath = pathlib.Path(dem.source())
    targetDEMPath = targetDir / "Inputs"
    try:
        shutil.copy(sourceDEMPath, targetDEMPath)
    except shutil.SameFileError:
        pass


def copyCfgFile(sourcePath, targetDir, destFileName):
    """copies a config ini file to targetDir/Inputs/CFG/<destFileName>

    Parameters
    -----------
    sourcePath: str
        path to the source config file
    targetDir: pathlib.Path
        base avalanche target directory
    destFileName: str
        destination filename (e.g. 'com2ABCfg.ini')
    """
    targetCFGPath = targetDir / "Inputs" / "CFGs"
    targetCFGPath.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy(sourcePath, targetCFGPath / destFileName)
    except shutil.SameFileError:
        pass


def copyRaster(raster, targetDir, suffix):
    """copies raster file to targetDir with suffix added to filename

    Parameters
    -----------
    raster:
        qgis raster layer
    targetDir: pathlib.Path
        target directory
    suffix: string
        suffix to add to filename (e.g., "_mu", "_k")
    """
    sourceRasterPath = pathlib.Path(raster.source())

    # Add suffix before file extension
    newFileName = sourceRasterPath.stem + suffix + sourceRasterPath.suffix
    targetRasterPath = targetDir / newFileName

    try:
        shutil.copy(sourceRasterPath, targetRasterPath)
    except shutil.SameFileError:
        pass


def copyMultipleRaster(rasterDict, targetDir, suffix):
    """copies multiple raster files to targetDir with suffix added to filenames

    Parameters
    -----------
    rasterDict:
        dict with multiple qgis raster layers
    targetDir: pathlib.Path
        target directory
    suffix: string
        suffix to add to filename (e.g., "_mu", "_k")
    """
    for raster in rasterDict:
        copyRaster(raster, targetDir, suffix)


def copyMultipleShp(sourceDict, targetPath, addToName=""):
    """copies multiple shapefile parts to targetPath

    Parameters
    -----------
    sourceDict:
        dict with multiple qgis source of shapefiles (path string)
    targetPath: string
        path to where the files are being copied (directory)
    addToName: string
        add this string to shape name
    """
    for source in sourceDict:
        copyShp(source, targetPath, addToName)


def copyShp(source, targetPath, addToName=""):
    """copies shapefile parts to targetPath

    Parameters
    -----------
    source:
        qgis source of shapefile (path string)
    targetPath: string
        path to where the files are being copied (directory)
    addToName: string
        add this string to shape name
    """
    sourcePath = pathlib.Path(source)

    shpParts = getSHPParts(sourcePath)
    for shpPart in shpParts:
        nName = shpPart.stem + addToName + shpPart.suffix
        nTargetPath = targetPath / nName
        try:
            shutil.copy(shpPart, nTargetPath)
        except shutil.SameFileError:
            pass


def getSHPParts(base):
    """Get all files of a shapefile

    Parameters
    -----------
    base: pathlib path
        to .shp file
    Returns
    -------
    generator with all shapefile parts
    """

    globBase = base.parent
    globbed = globBase.glob(base.stem + ".*")

    return globbed


# TODO: maybe combine this with getLatestPeak
def getLatestPeakCom8(targetDir):
    """Get latest peakFiles of com8MoTPSA results

    Parameters
    -----------
    targetDir: pathlib path
        to avalanche directory
    Returns
    -------
    rasterResults: dataframe
        dataframe with info about simulations, including path
    """
    avaDir = pathlib.Path(str(targetDir))
    inputDirPeak = avaDir / "Outputs" / "com8MoTPSA" / "peakFiles"
    allRasterResults = fU.makeSimDF(inputDirPeak, avaDir=avaDir)

    return allRasterResults

def getLatestPeakCom9(targetDir):
    """Get latest peakFiles of com9MoTVoellmy results

    Parameters
    -----------
    targetDir: pathlib path
        to avalanche directory
    Returns
    -------
    rasterResults: dataframe
        dataframe with info about simulations, including path
    """
    avaDir = pathlib.Path(str(targetDir))
    inputDirPeak = avaDir / "Outputs" / "com9MoTVoellmy" / "peakFiles"
    allRasterResults = fU.makeSimDF(inputDirPeak, avaDir=avaDir)

    return allRasterResults

def getLatestPeak(targetDir):
    """Get latest peakFiles of com1DFA results

    Parameters
    -----------
    targetDir: pathlib path
        to avalanche directory
    Returns
    -------
    rasterResults: dataframe
        dataframe with info about simulations, including path
    """
    avaDir = pathlib.Path(str(targetDir))
    inputDirPeak = avaDir / "Outputs" / "com1DFA" / "peakFiles"
    allRasterResults = fU.makeSimDF(inputDirPeak, avaDir=avaDir)

    # Get info about latest simulations
    inputDirConf = avaDir / "Outputs" / "com1DFA" / "configurationFiles"
    latestCsv = inputDirConf / "latestSims.csv"
    with open(latestCsv, "rb") as file:
        latestResults = pd.read_csv(file, index_col=0, keep_default_na=False)

    # Only use results from latest run
    rasterResults = allRasterResults[allRasterResults.simID.isin(latestResults.index)]

    return rasterResults


def getAlphaBetaResults(targetDir, useSmallAva=False):
    """Get results of com2AB

    Parameters
    -----------
    targetDir: pathlib path
        to avalanche directory
    useSmallAva: boolean
        whether to look for small avalanche results

    Returns
    -------

    """
    from qgis.core import QgsVectorLayer

    avaDir = pathlib.Path(str(targetDir))
    if useSmallAva:
        abResultsFile = avaDir / "Outputs" / "com2AB" / "com2AB_Results_small.shp"
    else:
        abResultsFile = avaDir / "Outputs" / "com2AB" / "com2AB_Results.shp"

    if pathlib.Path.is_file(abResultsFile):
        abResultsLayer = QgsVectorLayer(str(abResultsFile), "AlphaBeta (com2)", "ogr")
        return abResultsLayer
    else:
        return 'None'

def getDFAPathResults(targetDir):
    '''Get results from path generation

        Parameters
        -----------
        targetDir: pathlib path
            to avalanche directory
        Returns
        -------
        DFAPathResults : massAvgPath and splitPoint
    '''
    from qgis.core import (QgsVectorLayer)
    avaDir = pathlib.Path(str(targetDir))
    pathDir = avaDir / 'Outputs' / 'ana5Utils' / 'DFAPath'
    allDFAPathLayers = []

    # Collect all path shapefiles
    for file in pathDir.glob('massAvgPath*.shp'):
        pathLayer = QgsVectorLayer(str(file), f"Mass Average Path - {file.stem}", "ogr")
        if pathLayer.isValid():
            allDFAPathLayers.append(pathLayer)

    # Collect all split point shapefiles
    for file in pathDir.glob('splitPointParabolicFit*.shp'):
        splitPointLayer = QgsVectorLayer(str(file), f"Split Point - {file.stem}", "ogr")
        if splitPointLayer.isValid():
            allDFAPathLayers.append(splitPointLayer)

    return allDFAPathLayers

def getCom6ScarpResults(targetDir):
    """Get results of com6 scarp analysis

    Parameters
    -----------
    targetDir: pathlib path
        to avalanche directory
    Returns
    -------

    """
    from qgis.core import QgsRasterLayer

    avaDir = pathlib.Path(str(targetDir))
    scarpResultsDir = avaDir / "Outputs" / "com6RockAvalanche" / "scarp"
    print("--------------")
    print(scarpResultsDir)

    globbed = list(scarpResultsDir.glob("*.asc")) + list(scarpResultsDir.glob("*.tif"))
    scriptDir = pathlib.Path(__file__).parent
    qml = str(scriptDir / "QGisStyles" / "probMap.qml")

    allRasterLayers = list()
    for item in globbed:
        rstLayer = QgsRasterLayer(str(item), item.stem)
        # try:
        #     rstLayer.loadNamedStyle(qml)
        # except:
        #     pass

        allRasterLayers.append(rstLayer)

    return allRasterLayers

def getAna4ProbAnaResults(targetDir):
    """Get results of ana4PropAna

    Parameters
    -----------
    targetDir: pathlib path
        to avalanche directory
    Returns
    -------

    """
    from qgis.core import QgsRasterLayer

    avaDir = pathlib.Path(str(targetDir))
    ana4ResultsDir = avaDir / "Outputs" / "ana4Stats"

    globbed = list(ana4ResultsDir.glob(avaDir.stem + "*.asc")) + list(ana4ResultsDir.glob(avaDir.stem + "*.tif"))
    scriptDir = pathlib.Path(__file__).parent
    qml = str(scriptDir / "QGisStyles" / "probMap.qml")

    allRasterLayers = list()
    for item in globbed:
        rstLayer = QgsRasterLayer(str(item), item.stem)
        try:
            rstLayer.loadNamedStyle(qml)
        except:
            pass

        allRasterLayers.append(rstLayer)

    return allRasterLayers


def addStyleToCom1DFAResults(rasterResults):
    """add QML Style to com1DFA raster results

    Parameters
    -----------
    rasterResults: dataframe
        com1DFA results from makeSimDF / getLatestPeak
    Returns
    -------
    allRasterLayers: list
        list of QGis raster layers with name and style; timeInfo results are excluded

    """
    from qgis.core import QgsRasterLayer

    scriptDir = pathlib.Path(__file__).parent
    qmls = dict()
    qmls["ppr"] = str(scriptDir / "QGisStyles" / "ppr.qml")
    qmls["pft"] = str(scriptDir / "QGisStyles" / "pft.qml")
    qmls["pfd"] = str(scriptDir / "QGisStyles" / "pft.qml")
    qmls["pfv"] = str(scriptDir / "QGisStyles" / "pfv.qml")
    qmls["PR"] = str(scriptDir / "QGisStyles" / "ppr.qml")
    qmls["FV"] = str(scriptDir / "QGisStyles" / "pfv.qml")
    qmls["FT"] = str(scriptDir / "QGisStyles" / "pft.qml")
    filtered = rasterResults[rasterResults["resType"] != "timeInfo"]

    allRasterLayers = list()
    for index, row in filtered.iterrows():
        rstLayer = QgsRasterLayer(str(row["files"]), row["names"])
        try:
            rstLayer.loadNamedStyle(qmls[row["resType"]])
        except:
            pass

        allRasterLayers.append(rstLayer)

    return allRasterLayers


def addLayersToContext(context, layers, outTarget):
    """add multiple layers to qgis context

    Parameters
    -----------
    context: QGisProcessing context
    layers: list
        list of QGis layers to add
    Returns
    -------
    context:
        updated context
    """
    from qgis.core import QgsProcessingContext

    context.temporaryLayerStore().addMapLayers(layers)

    for item in layers:
        context.addLayerToLoadOnCompletion(
            item.id(),
            QgsProcessingContext.LayerDetails(
                item.name(), context.project(), outTarget
            ),
        )

    return context


def addSingleLayerToContext(context, layer, outTarget):
    """add layer to qgis context

    Parameters
    -----------
    context: QGisProcessing context
    layer:
        QGis layer to add
    Returns
    -------
    context:
        updated context
    """
    from qgis.core import QgsProcessingContext

    context.temporaryLayerStore().addMapLayer(layer)

    context.addLayerToLoadOnCompletion(
        layer.id(),
        QgsProcessingContext.LayerDetails(layer.name(), context.project(), outTarget),
    )

    return context


def moveInputAndOutputFoldersToFinal(targetDir, finalTargetDir):
    """Move input and output folders to finalTargetDir

    Parameters
    -----------
    finalTargetDir: path
        The directory in which the final results will end up
    targetDir: path
        The same, but with /tmp added
    Returns
    -------
    """
    shutil.copytree(
        targetDir / "Outputs", finalTargetDir / "Outputs", dirs_exist_ok=True
    )
    shutil.rmtree(targetDir / "Outputs")
    shutil.copytree(targetDir / "Inputs", finalTargetDir / "Inputs", dirs_exist_ok=True)
    shutil.rmtree(targetDir / "Inputs")
    logFile = list(targetDir.glob("*.log"))
    shutil.move(logFile[0], finalTargetDir)

    # remove tmp directory
    shutil.rmtree(targetDir)

    return "Success"


def createFolderStructure(foldDest):
    """create (tmp) folder structure

    Parameters
    -----------
    foldDest: path/str
        Destination folder
    Returns
    -------
    finalTargetDir: path
        The directory in which the final results will end up
    targetDir: path
        The same, but with /tmp added
    """

    finalTargetDir = pathlib.Path(foldDest)
    targetDir = finalTargetDir / "tmp"

    iP.initializeFolderStruct(targetDir, removeExisting=True)

    finalOutputs = finalTargetDir / "Outputs"
    if finalOutputs.is_dir():
        shutil.copytree(finalOutputs, targetDir / "Outputs", dirs_exist_ok=True)

    return finalTargetDir, targetDir


def analyseLogFromDir(simDir):
    """Searches simulation folder for latest log

    Parameters
    -----------
    simDir: path/str
        Simulation folder to search for log
    Returns
    -------
    """

    logFile = list(simDir.glob("*.log"))
    with open(logFile[-1], "r") as logF:
        for lineNumber, line in enumerate(logF):
            if "ERROR" in line:
                print("ERROR found in file")
                print("Line Number:", lineNumber)
                print("Line:", line)


def runAndCheck(command, self, feedback):
    """Run a subprocess via Qt (QProcess) and fail fast on errors.

    This avoids shell usage (which is flagged by QGIS plugin publishing checks)
    and integrates better with the Qt event loop for cross-platform stability.

    Parameters
    -----------
    command: list[str]
        Process command as argv list. The first element is the program, the
        remaining elements are arguments.
    self:
        QGIS algorithm instance (used for translations)
    feedback:
        QGIS processing feedback

    Raises
    ------
    QgsProcessingException
        If the process prints a line containing "ERROR", is cancelled, fails
        to start, or exits with a non-zero exit code.
    """

    from qgis.PyQt.QtCore import QEventLoop, QProcess, QTimer

    if not command:
        raise QgsProcessingException(self.tr("Empty command"))

    program = command[0]
    arguments = command[1:]

    process = QProcess()
    process.setProcessChannelMode(QProcess.MergedChannels)

    startTime = time.time()

    # State container for shared variables
    state = {
        "errorLine": None,
        "buffer": "",
        "timeStepCounter": 0,
        "startTime": startTime,
        "recentLines": [],  # Ring buffer of recent output for error reporting
    }

    loop = QEventLoop()

    # Setup Timers
    heartbeatTimer = QTimer()
    heartbeatTimer.setInterval(30000)
    heartbeatTimer.timeout.connect(lambda: _handleHeartbeat(feedback, startTime))

    cancelTimer = QTimer()
    cancelTimer.setInterval(200)
    cancelTimer.timeout.connect(lambda: _checkCancel(process, feedback, loop))

    # Connect signals
    process.readyRead.connect(
        lambda: _handleProcessOutput(process, feedback, loop, heartbeatTimer, state)
    )
    process.finished.connect(lambda: loop.quit())

    # Start process
    process.start(program, arguments)
    if not process.waitForStarted(30000):
        raise QgsProcessingException(self.tr(f"Failed to start process: {program}"))

    heartbeatTimer.start()
    cancelTimer.start()

    loop.exec()

    heartbeatTimer.stop()
    cancelTimer.stop()

    # Drain any remaining output
    _handleProcessOutput(process, feedback, loop, heartbeatTimer, state)

    if feedback.isCanceled():
        raise QgsProcessingException(self.tr("Cancelled"))

    if state["errorLine"] is not None:
        raise QgsProcessingException(self.tr(state["errorLine"]))

    exitCode = process.exitCode()
    if exitCode != 0:
        detailedError = ""
        if state["recentLines"]:
            detailedError = "\n\nRecent output:\n" + "\n".join(state["recentLines"])

        raise QgsProcessingException(
            self.tr(f"Process failed with exit code {exitCode}: {program}{detailedError}")
        )


def _getTimeStepReportEvery(currentTimeStepCounter):
    """Helper to determine report frequency based on progress"""
    if currentTimeStepCounter >= 10000:
        return 2000
    if currentTimeStepCounter >= 1000:
        return 500
    return 50


def _formatElapsed(startTime):
    elapsed = int(time.time() - startTime)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:d}:{minutes:02d}:{seconds:02d}"


def _handleHeartbeat(feedback, startTime):
    """Periodic message to show the process hasn't frozen"""
    feedback.pushInfo(f"Process is still running... ({_formatElapsed(startTime)})")


def _checkCancel(process, feedback, loop):
    """Monitor QGIS cancellation of the algorithm"""
    if feedback.isCanceled():
        process.kill()
        loop.quit()


def _handleProcessOutput(process, feedback, loop, heartbeatTimer, state):
    """Read QProcess output and update feedback/state"""
    data = bytes(process.readAll()).decode("utf-8", errors="replace")
    if not data:
        return

    state["buffer"] += data

    # AvaFrame sometimes prints progress using carriage returns ("\r") without newlines.
    # Treat both "\n" and "\r" as line delimiters.
    while True:
        nlIndex = state["buffer"].find("\n")
        crIndex = state["buffer"].find("\r")

        if nlIndex == -1 and crIndex == -1:
            break

        if nlIndex == -1:
            splitIndex = crIndex
        elif crIndex == -1:
            splitIndex = nlIndex
        else:
            splitIndex = min(nlIndex, crIndex)

        line = state["buffer"][:splitIndex]
        state["buffer"] = state["buffer"][splitIndex + 1 :]

        # Handle CRLF (\r\n) or (\n\r)
        if state["buffer"].startswith(("\n", "\r")):
            state["buffer"] = state["buffer"][1:]

        line = line.strip()
        if not line:
            continue

        # Keep a small ring buffer of output lines for debugging failures
        state["recentLines"].append(line)
        if len(state["recentLines"]) > 30:
            state["recentLines"].pop(0)

        # Fail fast on ERROR
        if "ERROR" in line and state["errorLine"] is None:
            state["errorLine"] = line
            process.kill()
            loop.quit()
            return

        # Forward warnings (but suppress normal chatter to avoid QGIS log truncation)
        if "WARNING" in line:
            feedback.pushInfo(line)
            heartbeatTimer.start()  # Reset heartbeat timer
            continue

        # Timestep progress: report on progressive intervals
        if "time step" in line:
            state["timeStepCounter"] += 1
            reportEvery = _getTimeStepReportEvery(state["timeStepCounter"])
            if state["timeStepCounter"] % reportEvery == 0:
                feedback.pushInfo(
                    "Process is running ({}). Reported time steps (all sims): {}".format(
                        _formatElapsed(state["startTime"]), state["timeStepCounter"]
                    )
                )
                heartbeatTimer.start()  # Reset heartbeat timer
            continue


# -----------------------------------------------------------------------------
# Legacy implementation (subprocess-based) - kept for reference/backup
# -----------------------------------------------------------------------------


def runAndCheck_legacy(command, self, feedback):
    """Legacy subprocess.Popen based implementation.

    Uses subprocess.Popen with shell=False and streams output to QGIS feedback.
    This is the old implementation kept for reference/backup.
    """
    import subprocess

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
        encoding="utf-8",
        errors="replace",
        universal_newlines=True,
    )

    printCounter = 0
    counter = 1

    while True:
        realtimeOutput = process.stdout.readline()

        if realtimeOutput == "" and process.poll() is not None:
            break

        if realtimeOutput:
            line = realtimeOutput.strip()

            # do not pollute output window with time step prints
            if "time step" in line:
                counter = counter + 1
                printCounter = printCounter + 1
                if printCounter > 100:
                    msg = (
                        "Process is running. Reported time steps (all sims): "
                        + str(counter)
                    )
                    feedback.pushInfo(msg)
                    printCounter = 0

            # Handle ERRORs
            elif "ERROR" in line:
                raise QgsProcessingException(self.tr(line))
            else:
                print(line, flush=True)
                feedback.pushInfo(line)

