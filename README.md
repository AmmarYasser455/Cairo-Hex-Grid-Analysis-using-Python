# Cairo Hex Grid Analysis (snippet)

This repository contains a script to create a projected hex grid over a place (e.g., Cairo), aggregate OpenStreetMap amenities into hex cells, score cells by service density/diversity, find cafe hotspots with DBSCAN, export GeoJSON, and create an interactive Folium map.

## Tested environment
- Python: 3.9 — 3.11
- Key packages (pinned in `requirements.txt`): geopandas, osmnx, folium, shapely, scikit-learn, pandas, numpy.

## Installation

### Recommended (conda — best for geospatial dependencies)
1. Create environment:
   ```
   conda create -n hexenv python=3.10 -y
   conda activate hexenv
   ```
2. Install from conda-forge:
   ```
   conda install -c conda-forge geopandas osmnx folium shapely fiona rtree pyproj scikit-learn branca pandas numpy matplotlib -y
   ```
3. (Optional) If you also want to pin exact versions from `requirements.txt`, you can then:
   ```
   pip install -r requirements.txt
   ```

### Pip (virtualenv)
1. Create and activate a virtualenv:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
2. Install:
   ```
   pip install -r requirements.txt
   ```

Note: Installing geospatial libs via pip on some systems requires system libraries (GDAL/PROJ/GEOS). Using conda-forge is generally easier.

## Usage

Basic usage (the script is `advanced_hex_analysis.py`):
```
python advanced_hex_analysis.py
```

Key variables at the top of the script you can change:
- `place_name` — the target place string for OSMnx geocoding (e.g., `"Cairo, Egypt"`).
- `hex_radius_m` — hex radius in meters.
- `output_folder` — where GeoJSON and HTML map are saved.
- DBSCAN parameters (in-script): `eps` (meters) and `min_samples` — consider making these configurable.

Outputs (default `output` folder):
- `cairo_hexgrid.geojson` — hex cells with counts/diversity/score.
- `hotspots.geojson` — detected cafe hotspots (if any).
- `cairo_hex_map.html` — interactive Folium map.

## Notes & Troubleshooting

- OSMnx API changes: some function names may change across OSMnx versions (e.g., `geometries_from_place` vs `features_from_place`). If you get errors, check your installed osmnx version and update function calls accordingly.
- If `pip install` fails for geopandas/fiona/shapely, prefer installing via conda-forge which handles binary dependencies.
- On Windows, installing `rtree` may require `libspatialindex` available (conda-forge handles this).
- If you see unusually large hex grids or memory issues, consider limiting the grid to a buffered convex hull of the amenity points rather than the entire administrative area.
- DBSCAN `eps` is in projected units (meters for EPSG:3857). If you change `hex_radius_m`, consider scaling `eps` accordingly.

## Next steps you might want
- Convert the script into a CLI with `argparse` to pass place, radius, DBSCAN params, and amenity list.
- Add unit tests for grid creation and scoring.
- Add a small sample dataset + expected outputs for CI/testing.

If you'd like, I can:
- produce a complete README (extended with examples/screenshots),
- refactor the script to accept CLI args,
- or prepare a conda environment YAML for reproducible installs.
