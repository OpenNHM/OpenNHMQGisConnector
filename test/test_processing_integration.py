"""Integration tests for QGIS Processing algorithms.

These tests run the actual plugin algorithms via processing.run() against the
bundled test data in test/data/avaSlide/Inputs/. They exercise the same code path a user triggers
when clicking "Run" in the QGIS Processing toolbox, including result loading
and style application.

By passing our own QgsProcessingContext to processing.run(), the output layers
survive after the call returns, so we can inspect their renderers, styles, and
layer-load-on-completion registration.

Requirements:
    - QGIS Python bindings (qgis conda package)
    - avaframe installed
    - QT_QPA_PLATFORM=offscreen (set automatically below for headless CI)

Run with:
    QT_QPA_PLATFORM=offscreen pixi run python -m pytest test/test_processing_integration.py -v

Slow tests (com5snowslide) are marked with @pytest.mark.slow and skipped by default.
Run them with:
    QT_QPA_PLATFORM=offscreen pixi run python -m pytest test/test_processing_integration.py -v -m slow
"""

import os
import sys
import pathlib
import shutil
import tempfile

import pytest

# Force offscreen rendering so tests work without a display / under xvfb
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# ---------------------------------------------------------------------------
# QGIS bootstrap -- must happen once before any processing.run() call
# ---------------------------------------------------------------------------

# Make the plugin importable as "OpenNHMQGisConnector"
PLUGIN_DIR = pathlib.Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qgis.core import (
    QgsApplication,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)


@pytest.fixture(scope="session")
def qgis_app():
    """Start a QgsApplication and initialize Processing + our provider."""
    app = QgsApplication([], False)
    app.initQgis()

    import processing
    from processing.core.Processing import Processing
    Processing.initialize()

    from OpenNHMQGisConnector.OpenNHMQGisConnector_provider import (
        OpenNHMQGisConnectorProvider,
    )
    provider = OpenNHMQGisConnectorProvider()
    app.processingRegistry().addProvider(provider)

    yield app

    # Skip exitQgis() -- it can segfault during Qt/C++ teardown in
    # headless mode, and the process is exiting anyway.


@pytest.fixture()
def context():
    """A QgsProcessingContext we own, so layers survive processing.run()."""
    ctx = QgsProcessingContext()
    ctx.setProject(QgsProject.instance())
    return ctx


@pytest.fixture()
def feedback():
    """QgsProcessingFeedback that collects messages for later assertions."""
    fb = QgsProcessingFeedback()
    messages = []
    fb.pushInfo = lambda msg: messages.append(msg)
    fb.messages = messages
    return fb


@pytest.fixture()
def dem_layer():
    """Load the bundled test DEM as a QgsRasterLayer."""
    path = str(PLUGIN_DIR / "test" / "data" / "avaSlide" / "Inputs" / "slideTopo.asc")
    layer = QgsRasterLayer(path, "dem")
    assert layer.isValid(), f"DEM not valid: {path}"
    QgsProject.instance().addMapLayer(layer)
    yield layer
    QgsProject.instance().removeMapLayer(layer.id())


@pytest.fixture()
def rel_layer():
    """Load the bundled release shapefile as a QgsVectorLayer."""
    path = str(PLUGIN_DIR / "test" / "data" / "avaSlide" / "Inputs" / "REL" / "slideRelease.shp")
    layer = QgsVectorLayer(path, "rel", "ogr")
    assert layer.isValid(), f"REL not valid: {path}"
    QgsProject.instance().addMapLayer(layer)
    yield layer
    QgsProject.instance().removeMapLayer(layer.id())


@pytest.fixture()
def ent_layer():
    """Load the bundled entrainment shapefile as a QgsVectorLayer."""
    path = str(PLUGIN_DIR / "test" / "data" / "avaSlide" / "Inputs" / "ENT" / "slideEntrainment.shp")
    layer = QgsVectorLayer(path, "ent", "ogr")
    assert layer.isValid(), f"ENT not valid: {path}"
    QgsProject.instance().addMapLayer(layer)
    yield layer
    QgsProject.instance().removeMapLayer(layer.id())


@pytest.fixture()
def res_layer():
    """Load the bundled resistance shapefile as a QgsVectorLayer."""
    path = str(PLUGIN_DIR / "test" / "data" / "avaSlide" / "Inputs" / "RES" / "slideResistance.shp")
    layer = QgsVectorLayer(path, "res", "ogr")
    assert layer.isValid(), f"RES not valid: {path}"
    QgsProject.instance().addMapLayer(layer)
    yield layer
    QgsProject.instance().removeMapLayer(layer.id())


@pytest.fixture()
def profile_layer():
    """Load the bundled AB profile line shapefile."""
    path = str(PLUGIN_DIR / "test" / "data" / "avaSlide" / "Inputs" / "LINES" / "slideProfiles_AB.shp")
    layer = QgsVectorLayer(path, "profile", "ogr")
    assert layer.isValid(), f"Profile not valid: {path}"
    QgsProject.instance().addMapLayer(layer)
    yield layer
    QgsProject.instance().removeMapLayer(layer.id())


@pytest.fixture()
def splitpoints_layer():
    """Load the bundled split-points shapefile."""
    path = str(PLUGIN_DIR / "test" / "data" / "avaSlide" / "Inputs" / "POINTS" / "slidePoints.shp")
    layer = QgsVectorLayer(path, "splitpoints", "ogr")
    assert layer.isValid(), f"Splitpoints not valid: {path}"
    QgsProject.instance().addMapLayer(layer)
    yield layer
    QgsProject.instance().removeMapLayer(layer.id())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Expected QML style per result type: renderer type and color ramp item count.
EXPECTED_STYLES = {
    "ppr": ("singlebandpseudocolor", 5),
    "pft": ("singlebandpseudocolor", 7),
    "pfv": ("singlebandpseudocolor", 8),
}


def get_color_ramp_items(layer):
    """Return color ramp items from a raster layer's renderer, or None."""
    renderer = layer.renderer()
    if renderer is None or not hasattr(renderer, "shader"):
        return None
    shader = renderer.shader()
    if shader is None:
        return None
    func = shader.rasterShaderFunction()
    if func is None or not hasattr(func, "colorRampItemList"):
        return None
    return func.colorRampItemList()


def assert_com1dfa_outputs(context, peak_dir):
    """Shared assertions for any com1DFA-style output: files, layers, styles."""
    assert peak_dir.is_dir(), "peakFiles directory not created"

    peak_files = list(peak_dir.glob("*.asc")) + list(peak_dir.glob("*.tif"))
    assert len(peak_files) >= 3, (
        f"Expected >= 3 peak files (pft, pfv, ppr), got {len(peak_files)}"
    )

    load_details = context.layersToLoadOnCompletion()
    assert len(load_details) >= 3, (
        f"Expected >= 3 layers registered for UI loading, got {len(load_details)}"
    )

    store = context.temporaryLayerStore()
    stored = store.mapLayers()
    assert len(stored) >= 3, f"Expected >= 3 layers in temp store, got {len(stored)}"

    for layer_id, layer in stored.items():
        assert layer.isValid(), f"Layer {layer.name()} is not valid"

        name = layer.name()
        res_type = next(
            (s for s in EXPECTED_STYLES if name.endswith(f"_{s}")), None
        )
        if res_type is None:
            continue  # e.g. timeInfo -- no custom style expected

        expected_renderer, expected_items = EXPECTED_STYLES[res_type]
        renderer = layer.renderer()
        assert renderer is not None, f"Layer {name}: no renderer (style not applied)"
        assert renderer.type() == expected_renderer, (
            f"Layer {name}: expected renderer '{expected_renderer}', "
            f"got '{renderer.type()}'"
        )
        items = get_color_ramp_items(layer)
        assert items is not None, f"Layer {name}: could not read color ramp"
        assert len(items) == expected_items, (
            f"Layer {name}: expected {expected_items} color ramp items, "
            f"got {len(items)}"
        )

    for layer_id, detail in load_details.items():
        assert detail.name, f"Layer {layer_id} has empty name in load details"


# ---------------------------------------------------------------------------
# 1. GetVersion
# ---------------------------------------------------------------------------


class TestGetVersion:
    """Smoke test: no I/O, just verifies the algorithm runs and reports version."""

    def test_returns_version_in_feedback(self, qgis_app, feedback):
        import processing

        result = processing.run(
            "OpenNHM:GetVersion",
            {"INPUT": "test"},
            feedback=feedback,
        )
        assert result == {}
        version_msgs = [m for m in feedback.messages if "AvaFrame Version" in m]
        assert len(version_msgs) == 1


# ---------------------------------------------------------------------------
# 2. GetDefaultModuleIni
# ---------------------------------------------------------------------------


class TestGetDefaultModuleIni:
    """Verifies each module's default ini can be extracted to a file."""

    @pytest.mark.parametrize("module_index,module_name", [
        (0, "com1DFA"),
        (1, "com2AB"),
        (2, "com5SnowSlide"),
        (3, "com6RockAvalanche"),
        (4, "com6Scarp"),
        (6, "com9MoTVoellmy"),
    ])
    def test_extracts_ini_file(self, qgis_app, context, feedback, module_index, module_name):
        import processing

        with tempfile.NamedTemporaryFile(suffix=".ini", delete=False) as f:
            dest = f.name
        try:
            result = processing.run(
                "OpenNHM:getdefaultmoduleini",
                {"MODULE": module_index, "OUTPUT_FILE": dest},
                feedback=feedback,
                context=context,
            )
            out_path = pathlib.Path(result["OUTPUT_FILE"])
            assert out_path.is_file(), f"No ini file written for {module_name}"
            assert out_path.stat().st_size > 0, f"Empty ini file for {module_name}"
            content = out_path.read_text()
            assert "[" in content, f"ini file for {module_name} looks invalid"
        finally:
            pathlib.Path(dest).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 3. In1RelInfo
# ---------------------------------------------------------------------------


class TestIn1RelInfo:
    """Release area statistics tool: verifies CSV output is produced."""

    def test_produces_release_info_csv(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            processing.run(
                "OpenNHM:in1relinfo",
                {"DEM": dem_layer, "REL": [rel_layer], "FOLDEST": tmpdir},
                feedback=feedback,
                context=context,
            )
            info_dir = pathlib.Path(tmpdir) / "Outputs" / "com1DFA" / "releaseInfoFiles"
            assert info_dir.is_dir(), "releaseInfoFiles directory not created"
            csv_files = list(info_dir.glob("*.csv"))
            assert len(csv_files) >= 1, "No release info CSV produced"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 4. com2AB
# ---------------------------------------------------------------------------


class TestCom2AB:
    """Alpha Beta: verifies vector output, layer loading, and validity."""

    def test_produces_vector_output_registered_for_loading(
        self, qgis_app, context, feedback, dem_layer, profile_layer, splitpoints_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            result = processing.run(
                "OpenNHM:com2ab",
                {
                    "DEM": dem_layer,
                    "PROFILE": profile_layer,
                    "SPLITPOINTS": splitpoints_layer,
                    "SMALLAVA": False,
                    "CFGFILE": None,
                    "FOLDEST": tmpdir,
                },
                feedback=feedback,
                context=context,
            )

            # Output file exists
            ab_dir = pathlib.Path(tmpdir) / "Outputs" / "com2AB"
            assert ab_dir.is_dir(), "com2AB output directory not created"
            result_shp = ab_dir / "com2AB_Results.shp"
            assert result_shp.is_file(), "com2AB_Results.shp not found"

            # Layer registered for UI loading
            load_details = context.layersToLoadOnCompletion()
            assert len(load_details) >= 1, "No layers registered for UI loading"

            # Layer in temp store is valid
            stored = context.temporaryLayerStore().mapLayers()
            assert len(stored) >= 1, "No layers in temp store"
            for layer in stored.values():
                assert layer.isValid(), f"com2AB layer {layer.name()} is not valid"

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 5 & 6. com1DFA
# ---------------------------------------------------------------------------


class TestCom1DFA:
    """Dense Flow: verifies simulation output, styles, and UI layer registration."""

    def test_minimal_dem_and_rel_only(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            processing.run(
                "OpenNHM:com1denseflow",
                {
                    "DEM": dem_layer,
                    "REL": [rel_layer],
                    "SECREL": None,
                    "ENT": None,
                    "RES": None,
                    "FRICTSIZE": 0,
                    "CFGFILE": None,
                    "FOLDEST": tmpdir,
                },
                feedback=feedback,
                context=context,
            )
            peak_dir = pathlib.Path(tmpdir) / "Outputs" / "com1DFA" / "peakFiles"
            assert_com1dfa_outputs(context, peak_dir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_with_entrainment_and_resistance(
        self, qgis_app, context, feedback, dem_layer, rel_layer, ent_layer, res_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            processing.run(
                "OpenNHM:com1denseflow",
                {
                    "DEM": dem_layer,
                    "REL": [rel_layer],
                    "SECREL": None,
                    "ENT": ent_layer,
                    "RES": res_layer,
                    "FRICTSIZE": 0,
                    "CFGFILE": None,
                    "FOLDEST": tmpdir,
                },
                feedback=feedback,
                context=context,
            )
            peak_dir = pathlib.Path(tmpdir) / "Outputs" / "com1DFA" / "peakFiles"
            assert_com1dfa_outputs(context, peak_dir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 7. com5SnowSlide
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestCom5SnowSlide:
    """Snow Slide: verifies vector outputs (raster-to-polygon) are produced and styled."""

    def test_produces_styled_vector_outputs(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            processing.run(
                "OpenNHM:com5snowslide",
                {
                    "DEM": dem_layer,
                    "REL": [rel_layer],
                    "RES": None,
                    "CFGFILE": None,
                    "FOLDEST": tmpdir,
                },
                feedback=feedback,
                context=context,
            )

            # Layers registered for UI loading
            load_details = context.layersToLoadOnCompletion()
            assert len(load_details) >= 1, "No layers registered for UI loading"

            # Layers in temp store are valid vector layers with styles applied
            stored = context.temporaryLayerStore().mapLayers()
            assert len(stored) >= 1, "No layers in temp store"
            for layer in stored.values():
                assert layer.isValid(), f"Layer {layer.name()} is not valid"
                assert layer.renderer() is not None, (
                    f"Layer {layer.name()}: no renderer (style not applied)"
                )

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 8. DFA Path Generation
# ---------------------------------------------------------------------------


class TestDFAPath:
    """DFA Path Generation: verifies massAvgPath and splitPoint shapefiles are produced.

    Note: the algorithm returns a list from OUTPUT (declared as
    QgsProcessingOutputVectorLayer), which causes processing.run() to raise
    TypeError during result unpacking. The simulation itself succeeds; we
    catch the error and verify outputs directly.
    """

    def test_produces_path_and_splitpoint_shapefiles(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            try:
                processing.run(
                    "OpenNHM:dfapath",
                    {"DEM": dem_layer, "REL": [rel_layer], "FOLDEST": tmpdir},
                    feedback=feedback,
                    context=context,
                )
            except TypeError:
                # Known issue: algorithm returns list for a VectorLayer output,
                # causing processing.run() to fail during result unpacking.
                # Outputs are still written; we verify below.
                pass

            path_dir = (
                pathlib.Path(tmpdir) / "Outputs" / "ana5Utils" / "DFAPath"
            )
            assert path_dir.is_dir(), "DFAPath output directory not created"

            mass_avg = list(path_dir.glob("massAvgPath*.shp"))
            assert len(mass_avg) >= 1, "No massAvgPath shapefile produced"

            split_pts = list(path_dir.glob("splitPointParabolicFit*.shp"))
            assert len(split_pts) >= 1, "No splitPoint shapefile produced"

            # Layers are in temp store despite the TypeError
            stored = context.temporaryLayerStore().mapLayers()
            assert len(stored) >= 2, (
                f"Expected >= 2 path layers in temp store, got {len(stored)}"
            )
            for layer in stored.values():
                assert layer.isValid(), f"Path layer {layer.name()} is not valid"

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 9. com9MoTVoellmy (basic)
# ---------------------------------------------------------------------------


class TestCom9MoTVoellmy:
    """MoTVoellmy: basic mode (constant friction, no entrainment, no forest)."""

    def test_basic_constant_friction_vector_release(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            processing.run(
                "OpenNHM:com9motvoellmy",
                {
                    "DEM": dem_layer,
                    "RELSHP": [rel_layer],
                    "RELRAS": None,
                    "FRICTION": 0,   # Constant
                    "MU": None,
                    "K": None,
                    "ENTRAINMENT": 0,  # No entrainment
                    "B0": None,
                    "TAUC": None,
                    "FOREST": 0,  # No forest
                    "ND": None,
                    "BHD": None,
                    "CFGFILE": None,
                    "FOLDEST": tmpdir,
                },
                feedback=feedback,
                context=context,
            )
            peak_dir = (
                pathlib.Path(tmpdir) / "Outputs" / "com9MoTVoellmy" / "peakFiles"
            )
            assert peak_dir.is_dir(), "com9 peakFiles directory not created"
            peak_files = list(peak_dir.glob("*.asc")) + list(peak_dir.glob("*.tif"))
            assert len(peak_files) >= 1, "No peak files produced by com9MoTVoellmy"

            load_details = context.layersToLoadOnCompletion()
            assert len(load_details) >= 1, "No layers registered for UI loading"

            stored = context.temporaryLayerStore().mapLayers()
            assert len(stored) >= 1, "No layers in temp store"
            for layer in stored.values():
                assert layer.isValid(), f"Layer {layer.name()} is not valid"

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 10. Load Peak Files
# ---------------------------------------------------------------------------


class TestLoadPeakFiles:
    """Load Peak Files: verifies styled raster layers are loaded from an existing run."""

    def test_loads_and_styles_peak_files(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        # Run com1DFA first to get an output directory with peak files
        com1_tmpdir = tempfile.mkdtemp()
        try:
            com1_ctx = QgsProcessingContext()
            com1_ctx.setProject(QgsProject.instance())
            processing.run(
                "OpenNHM:com1denseflow",
                {
                    "DEM": dem_layer,
                    "REL": [rel_layer],
                    "SECREL": None,
                    "ENT": None,
                    "RES": None,
                    "FRICTSIZE": 0,
                    "CFGFILE": None,
                    "FOLDEST": com1_tmpdir,
                },
                feedback=QgsProcessingFeedback(),
                context=com1_ctx,
            )

            # Now load peak files from that directory
            processing.run(
                "OpenNHM:loadpeakfiles",
                {
                    "PEAKDIR": com1_tmpdir,
                    "RESTYPES": [0, 1, 2],  # ppr, pft, pfv
                },
                feedback=feedback,
                context=context,
            )

            load_details = context.layersToLoadOnCompletion()
            assert len(load_details) >= 3, (
                f"Expected >= 3 peak layers registered for UI loading, "
                f"got {len(load_details)}"
            )

            stored = context.temporaryLayerStore().mapLayers()
            assert len(stored) >= 3, "Expected >= 3 peak layers in temp store"

            for layer in stored.values():
                assert layer.isValid(), f"Peak layer {layer.name()} is not valid"
                name = layer.name()
                res_type = next(
                    (s for s in EXPECTED_STYLES if name.endswith(f"_{s}")), None
                )
                if res_type is None:
                    continue
                renderer = layer.renderer()
                assert renderer is not None, (
                    f"Layer {name}: no renderer after loadpeakfiles"
                )
                assert renderer.type() == EXPECTED_STYLES[res_type][0], (
                    f"Layer {name}: wrong renderer type"
                )

        finally:
            shutil.rmtree(com1_tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 11. Layer Rename
# ---------------------------------------------------------------------------


class TestLayerRename:
    """Layer Rename: verifies com1DFA output layers are renamed with a parameter value."""

    def test_renames_peak_layers(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        # Run com1DFA to get peak layers in the temp store
        com1_tmpdir = tempfile.mkdtemp()
        try:
            com1_ctx = QgsProcessingContext()
            com1_ctx.setProject(QgsProject.instance())
            processing.run(
                "OpenNHM:com1denseflow",
                {
                    "DEM": dem_layer,
                    "REL": [rel_layer],
                    "SECREL": None,
                    "ENT": None,
                    "RES": None,
                    "FRICTSIZE": 0,
                    "CFGFILE": None,
                    "FOLDEST": com1_tmpdir,
                },
                feedback=QgsProcessingFeedback(),
                context=com1_ctx,
            )

            # Promote peak layers into the project so layerRename can find them
            peak_layers = list(com1_ctx.temporaryLayerStore().mapLayers().values())
            for layer in peak_layers:
                QgsProject.instance().addMapLayer(layer, False)

            original_names = [layer.name() for layer in peak_layers]

            processing.run(
                "OpenNHM:layerRename",
                {"LAYERS": peak_layers, "VARS": "rho"},
                feedback=feedback,
                context=context,
            )

            # Names should have changed (mu value appended)
            renamed_names = [layer.name() for layer in peak_layers]
            assert renamed_names != original_names, (
                "Layer names unchanged after layerRename -- rename had no effect"
            )

        finally:
            for layer in peak_layers:
                try:
                    QgsProject.instance().removeMapLayer(layer.id())
                except Exception:
                    pass
            shutil.rmtree(com1_tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 12. com7 Regional Splitting
# ---------------------------------------------------------------------------


class TestCom7RegionalSplitting:
    """Regional Splitting: verifies per-avalanche sub-directories are created."""

    def test_splits_input_into_subdirectories(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            processing.run(
                "OpenNHM:com7regionalsplitting",
                {
                    "DEM": dem_layer,
                    "REL": rel_layer,
                    "ENT": None,
                    "RES": None,
                    "FOLDEST": tmpdir,
                },
                feedback=feedback,
                context=context,
            )

            regional_dir = pathlib.Path(tmpdir) / "com7Regional"
            assert regional_dir.is_dir(), "com7Regional directory not created"

            sub_dirs = [
                d for d in regional_dir.iterdir()
                if d.is_dir() and d.name.isdigit()
            ]
            assert len(sub_dirs) >= 1, "No numbered sub-directories created by splitting"

            for sub in sub_dirs:
                assert (sub / "Inputs").is_dir(), (
                    f"Sub-directory {sub.name} has no Inputs folder"
                )

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 13. com7 Regional Computation
# ---------------------------------------------------------------------------


class TestCom7RegionalComputation:
    """Regional Computation: runs splitting then computation, verifies merged outputs."""

    def test_produces_merged_rasters(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            # Step 1: split inputs
            split_ctx = QgsProcessingContext()
            split_ctx.setProject(QgsProject.instance())
            processing.run(
                "OpenNHM:com7regionalsplitting",
                {
                    "DEM": dem_layer,
                    "REL": rel_layer,
                    "ENT": None,
                    "RES": None,
                    "FOLDEST": tmpdir,
                },
                feedback=QgsProcessingFeedback(),
                context=split_ctx,
            )

            # Step 2: run computation on the split output
            processing.run(
                "OpenNHM:com7regionalcomputation",
                {"FOLDEST": tmpdir},
                feedback=feedback,
                context=context,
            )

            regional_dir = pathlib.Path(tmpdir) / "com7Regional"
            merged_dir = regional_dir / "mergedRasters"
            assert merged_dir.is_dir(), "mergedRasters directory not created"

            merged_files = (
                list(merged_dir.glob("*.asc")) + list(merged_dir.glob("*.tif"))
            )
            assert len(merged_files) >= 1, "No merged raster files produced"

            all_peak_dir = regional_dir / "allPeakFiles"
            assert all_peak_dir.is_dir(), "allPeakFiles directory not created"
            all_peaks = (
                list(all_peak_dir.glob("*.asc")) + list(all_peak_dir.glob("*.tif"))
            )
            assert len(all_peaks) >= 1, "No individual peak files in allPeakFiles"

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 14. ana4ProbAna (Probability Run)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestAna4ProbAna:
    """Probability run: runs ~40 com1DFA sims with varied ci95, then probability analysis.

    Very slow (~5 min). Marked slow, skipped by default.
    The algorithm has the same list-return bug as dfapath -- returns a list for
    a QgsProcessingOutputVectorLayer output, causing TypeError in result unpacking.
    """

    def test_produces_probability_rasters_and_styled_layers(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            try:
                processing.run(
                    "OpenNHM:ana4probana",
                    {"DEM": dem_layer, "REL": [rel_layer], "FOLDEST": tmpdir},
                    feedback=feedback,
                    context=context,
                )
            except TypeError:
                # Known issue: algorithm returns list for a VectorLayer output.
                pass

            ana4_dir = pathlib.Path(tmpdir) / "Outputs" / "ana4Stats"
            assert ana4_dir.is_dir(), "ana4Stats output directory not created"

            prob_files = (
                list(ana4_dir.glob("*.asc")) + list(ana4_dir.glob("*.tif"))
            )
            assert len(prob_files) >= 1, "No probability raster files produced"

            # Layer registered for UI loading
            load_details = context.layersToLoadOnCompletion()
            assert len(load_details) >= 1, "No layers registered for UI loading"

            # Layer in temp store is valid and styled
            stored = context.temporaryLayerStore().mapLayers()
            assert len(stored) >= 1, "No layers in temp store"
            for layer in stored.values():
                assert layer.isValid(), f"Layer {layer.name()} is not valid"
                renderer = layer.renderer()
                assert renderer is not None, (
                    f"Layer {layer.name()}: no renderer (probMap style not applied)"
                )
                assert renderer.type() == "singlebandpseudocolor", (
                    f"Layer {layer.name()}: expected singlebandpseudocolor, "
                    f"got {renderer.type()}"
                )

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 15. ana4ProbDirOnly (Probability Analysis for existing directory)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestAna4ProbDirOnly:
    """Probability analysis on an existing com1DFA probability run directory.

    Depends on ana4probana output. Runs ana4probana first, clears ana4Stats,
    then re-runs probability analysis via ana4probdironly.
    Marked slow because the prerequisite ana4probana run is very slow.
    """

    def test_reanalyses_existing_prob_run_directory(
        self, qgis_app, context, feedback, dem_layer, rel_layer
    ):
        import processing

        tmpdir = tempfile.mkdtemp()
        try:
            # Step 1: run full probability simulation to create com1DFA outputs
            prob_ctx = QgsProcessingContext()
            prob_ctx.setProject(QgsProject.instance())
            try:
                processing.run(
                    "OpenNHM:ana4probana",
                    {"DEM": dem_layer, "REL": [rel_layer], "FOLDEST": tmpdir},
                    feedback=QgsProcessingFeedback(),
                    context=prob_ctx,
                )
            except TypeError:
                pass

            # Step 2: remove the ana4Stats output so we can verify it gets recreated
            ana4_dir = pathlib.Path(tmpdir) / "Outputs" / "ana4Stats"
            assert ana4_dir.is_dir(), "ana4Stats not created by prerequisite run"
            shutil.rmtree(ana4_dir)
            assert not ana4_dir.exists()

            # Step 3: run probability analysis only
            try:
                processing.run(
                    "OpenNHM:ana4probdironly",
                    {"FOLDEST": tmpdir},
                    feedback=feedback,
                    context=context,
                )
            except TypeError:
                pass

            assert ana4_dir.is_dir(), "ana4Stats not recreated by ana4probdironly"
            prob_files = (
                list(ana4_dir.glob("*.asc")) + list(ana4_dir.glob("*.tif"))
            )
            assert len(prob_files) >= 1, "No probability raster files produced"

            stored = context.temporaryLayerStore().mapLayers()
            assert len(stored) >= 1, "No layers in temp store"
            for layer in stored.values():
                assert layer.isValid(), f"Layer {layer.name()} is not valid"

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
