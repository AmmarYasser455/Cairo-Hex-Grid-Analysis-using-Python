"""The committed showcase outputs must match what make_showcase.py builds."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "showcase"


def _load():
    spec = importlib.util.spec_from_file_location(
        "make_showcase", SHOWCASE / "make_showcase.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("showcase")
    mod = _load()
    try:
        import matplotlib  # noqa: F401
        png = True
    except ImportError:
        png = False
    mod.write_outputs(out, png=png)
    return out, png


def test_geojson_matches_committed(built):
    out, _ = built
    new = json.loads((out / "map.geojson").read_text(encoding="utf-8"))
    old = json.loads((SHOWCASE / "map.geojson").read_text(encoding="utf-8"))
    assert new == old


def test_geojson_is_lonlat_over_cairo(built):
    out, _ = built
    fc = json.loads((out / "map.geojson").read_text(encoding="utf-8"))
    for f in fc["features"]:
        pts = f["geometry"]["coordinates"]
        while isinstance(pts[0], list):
            pts = pts[0]
        lon, lat = pts[0], pts[1]
        assert 31.1 < lon < 31.4 and 29.9 < lat < 30.2  # lon first, not lat


def test_png_produced(built):
    out, png = built
    if not png:
        pytest.skip("matplotlib not installed")
    assert (out / "map.png").stat().st_size > 10_000


def test_notebook_executes_offline():
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")
    pytest.importorskip("matplotlib")
    nb = nbformat.read(SHOWCASE / "showcase.ipynb", as_version=4)
    for c in nb.cells:  # drop saved outputs so only fresh results are checked
        if c.cell_type == "code":
            c.outputs = []
    nbclient.NotebookClient(
        nb, timeout=300, resources={"metadata": {"path": str(ROOT)}}
    ).execute()
    outs = [o for c in nb.cells if c.cell_type == "code" for o in c.outputs]
    assert not [o for o in outs if o.output_type == "error"]
    assert any("image/png" in o.get("data", {}) for o in outs)
