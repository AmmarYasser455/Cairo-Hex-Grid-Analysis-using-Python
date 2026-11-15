"""Build the central Cairo showcase (offline) from showcase/data/.

Run from the repository root:  python showcase/make_showcase.py

Writes map.geojson, map.png and index.html (and reads only showcase/data/).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box, mapping
from shapely.geometry.polygon import orient

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from hexanalysis import (  # noqa: E402
    aggregate_amenities,
    compute_scores,
    create_hex_grid_gdf,
    detect_hotspots,
)

DATA_FILE = HERE / "data" / "amenities_osm.geojson"
# Study area (lon/lat, EPSG:4326): west, south, east, north. Same box that was
# used for the Overpass query that produced the data file.
BBOX = (31.215, 30.030, 31.265, 30.075)
WORK_CRS = "EPSG:32636"  # WGS 84 / UTM zone 36N (metres); Cairo is at ~31.2 E
HEX_RADIUS_M = 300.0
DBSCAN_EPS_M = 150.0
DBSCAN_MIN_SAMPLES = 4
TITLE = "Central Cairo: everyday-amenity coverage on a 300 m hex grid"
CREDIT = "Data: (c) OpenStreetMap contributors, ODbL"
REPO_URL = "https://github.com/AmmarYasser455/Cairo-Hex-Grid-Analysis-using-Python"
ROUND = 6  # decimals for lon/lat (about 0.1 m)


def run_analysis(data_file: Path = DATA_FILE):
    """Return (hexes, amenities, hotspots) all in WORK_CRS (metres)."""
    amenities = gpd.read_file(data_file)  # GeoJSON: lon/lat, EPSG:4326
    if amenities.crs is None:
        amenities = amenities.set_crs("EPSG:4326")
    amenities = amenities.to_crs(WORK_CRS)
    area = gpd.GeoDataFrame(geometry=[box(*BBOX)], crs="EPSG:4326")
    hexes = create_hex_grid_gdf(area, HEX_RADIUS_M, crs=WORK_CRS)
    hexes = aggregate_amenities(amenities, hexes)
    hexes = compute_scores(hexes)
    hotspots = detect_hotspots(
        amenities, "cafe", eps=DBSCAN_EPS_M, min_samples=DBSCAN_MIN_SAMPLES
    )
    hexes["hex_id"] = range(len(hexes))
    return hexes, amenities, hotspots


def _round_coords(obj):
    if isinstance(obj, (list, tuple)):
        return [_round_coords(o) for o in obj]
    return round(float(obj), ROUND)


def _geom(geom):
    if geom.geom_type == "Polygon":
        geom = orient(geom, 1.0)  # RFC 7946: exterior counter-clockwise
    m = mapping(geom)
    return {"type": m["type"], "coordinates": _round_coords(m["coordinates"])}


def build_geojson(hexes, hotspots) -> dict:
    """Result as an RFC 7946 FeatureCollection in lon/lat."""
    hx = hexes.to_crs(4326)
    feats = []
    for _, r in hx.iterrows():
        feats.append({
            "type": "Feature",
            "geometry": _geom(r.geometry),
            "properties": {
                "kind": "hex",
                "hex_id": int(r["hex_id"]),
                "amenities": int(r["count"]),
                "types": int(r["diversity"]),
                "density_per_km2": round(float(r["density_per_km2"]), 1),
                "score": round(float(r["score"]), 3),
            },
        })
    if len(hotspots):
        for _, r in hotspots.to_crs(4326).iterrows():
            feats.append({
                "type": "Feature",
                "geometry": _geom(r.geometry),
                "properties": {"kind": "cafe_hotspot",
                               "cluster": int(r["cluster"]),
                               "cafes": int(r["size"])},
            })
    return {"type": "FeatureCollection", "features": feats}


def make_png(hexes, amenities, hotspots, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    hx = hexes.to_crs(4326)
    fig, ax = plt.subplots(figsize=(8.8, 8.4), dpi=150)
    hx.plot(ax=ax, column="score", cmap="YlOrRd", edgecolor="white",
            linewidth=0.4, vmin=0, vmax=1, legend=True,
            legend_kwds={"label": "Service score (0-1)", "shrink": 0.7})
    am = amenities.to_crs(4326)
    am.plot(ax=ax, color="#333333", markersize=2, alpha=0.5)
    if len(hotspots):
        hs = hotspots.to_crs(4326)
        hs.plot(ax=ax, marker="*", color="#1f5fbf", edgecolor="white",
                markersize=260, linewidth=0.8, zorder=5)
    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", color="#333333", markersize=4,
               label=f"Amenity ({len(am)})"),
        Line2D([], [], marker="*", ls="", color="#1f5fbf", markersize=14,
               markeredgecolor="white", label=f"Cafe hotspot ({len(hotspots)})"),
    ], loc="lower left", fontsize=9, framealpha=0.9)
    ax.set_title(TITLE, fontsize=12)
    ax.set_xlabel("Longitude (deg E, EPSG:4326)")
    ax.set_ylabel("Latitude (deg N)")
    ax.annotate("N", xy=(0.95, 0.95), xytext=(0.95, 0.88),
                xycoords="axes fraction", ha="center", fontsize=12,
                arrowprops={"arrowstyle": "-|>", "color": "black"})
    ax.text(0.99, 0.01, CREDIT, transform=ax.transAxes, ha="right",
            va="bottom", fontsize=7, color="#444444")
    ax.set_aspect(1 / 0.866)  # 1 deg lon ~ cos(30 deg) of 1 deg lat
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
 body { margin: 0; font-family: sans-serif; }
 header { padding: 8px 14px; background: #f5f5f5; border-bottom: 1px solid #ccc; }
 h1 { font-size: 18px; margin: 0 0 4px; }
 p { margin: 2px 0; font-size: 13px; }
 #map { height: calc(100vh - 100px); }
</style>
</head>
<body>
<header>
 <h1>__TITLE__</h1>
 <p>Each hexagon (300 m radius) is coloured by a 0-1 score: 65% amenity density, 35% number of amenity types. Blue circles mark clusters of cafes.</p>
 <p>Click a cell for its numbers. <a href="__REPO__">Source code and method</a>.</p>
</header>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var map = L.map('map');
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);
function colour(s) {
  return s > 0.75 ? '#bd0026' : s > 0.5 ? '#f03b20' : s > 0.25 ? '#fd8d3c' : s > 0.05 ? '#fecc5c' : '#ffffb2';
}
function popup(p) {
  return Object.keys(p).map(function (k) { return '<b>' + k + '</b>: ' + p[k]; }).join('<br>');
}
fetch('map.geojson').then(function (r) { return r.json(); }).then(function (data) {
  var layer = L.geoJSON(data, {
    style: function (f) {
      if (f.properties.kind === 'cafe_hotspot') {
        return { color: '#1f5fbf', weight: 2, fillColor: '#1f5fbf', fillOpacity: 1 };
      }
      return { color: '#fff', weight: 1, fillOpacity: 0.6, fillColor: colour(f.properties.score) };
    },
    pointToLayer: function (f, ll) {
      return L.circleMarker(ll, { radius: 9, color: '#fff', weight: 2, fillColor: '#1f5fbf', fillOpacity: 1 });
    },
    onEachFeature: function (f, l) { l.bindPopup(popup(f.properties)); }
  }).addTo(map);
  map.fitBounds(layer.getBounds());
});
</script>
</body>
</html>
"""


def write_outputs(outdir: Path, data_file: Path = DATA_FILE, png: bool = True):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    hexes, amenities, hotspots = run_analysis(data_file)
    fc = build_geojson(hexes, hotspots)
    (outdir / "map.geojson").write_text(
        json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    html = INDEX_HTML.replace("__TITLE__", TITLE).replace("__REPO__", REPO_URL)
    (outdir / "index.html").write_text(html, encoding="utf-8")
    if png:
        make_png(hexes, amenities, hotspots, outdir / "map.png")
    return hexes, amenities, hotspots


def main() -> None:
    hexes, amenities, hotspots = write_outputs(HERE)
    print(f"{len(amenities)} amenities, {len(hexes)} hexes, "
          f"{len(hotspots)} cafe hotspots -> {HERE}")


if __name__ == "__main__":
    main()
