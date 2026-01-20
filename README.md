# Cairo Hex Grid Analysis

An end-to-end script to analyze OpenStreetMap (OSM) amenities over Cairo using a projected hex grid. The project builds a hex grid, aggregates amenity counts and diversity, computes a service score per hex, detects cafe hotspots with DBSCAN, exports GeoJSON, and produces an interactive Folium map.

Live demo (interactive map)
- View the hosted interactive map here: https://cairo-hex-analysis-by-ammaryasser.netlify.app/

Quick links
- Script: `advanced_hex_analysis.py`
- Requirements: `requirements.txt`

Features
- Download OSM amenities for a place (default: Cairo, Egypt)
- Build a projected hex grid (meters) and trim to the target area
- Aggregate amenity counts and unique amenity diversity per hex
- Compute a combined "service score" (weighted density + diversity)
- Detect cafe hotspots using DBSCAN (projected distances)
- Export GeoJSONs and save an interactive Folium HTML map

Getting started

1. Clone the repo
```bash
git clone https://github.com/AmmarYasser455/Cairo-Hex-Grid-Analysis-using-Python.git
cd Cairo-Hex-Grid-Analysis-using-Python
```

2. Install dependencies
- Recommended: use conda (best for geospatial binaries)
```bash
conda create -n hexenv python=3.10 -y
conda activate hexenv
conda install -c conda-forge geopandas osmnx folium shapely fiona rtree pyproj scikit-learn branca pandas numpy matplotlib -y
# Optionally pin exact pip versions:
pip install -r requirements.txt
```

- Or with pip in a virtualenv:
```bash
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Run the analysis
- By default the script uses the variables at the top of `advanced_hex_analysis.py`:
  - `place_name` — e.g., `"Cairo, Egypt"`
  - `hex_radius_m` — hex radius in meters
  - `output_folder` — where outputs are saved
- Run:
```bash
python advanced_hex_analysis.py
```

Outputs (default `output/` folder)
- `cairo_hexgrid.geojson` — hex cells with attributes: count, diversity, area_m2, density_per_km2, score
- `hotspots.geojson` — detected cafe hotspots (if any)
- `cairo_hex_map.html` — interactive Folium map (this is the HTML you can view locally or host; the live demo link above hosts a version online)

Embedding / hosting the HTML map
- If you want to host the generated `cairo_hex_map.html` yourself:
  - Option A — GitHub Pages: place the HTML in the `gh-pages` branch or in a docs/ folder and enable GitHub Pages.
  - Option B — Netlify: drag & drop the HTML (or point Netlify to the repo) — this is how the live demo above was deployed.
- The README's "Live demo" link points to a Netlify-hosted copy of the generated HTML map.

Notes & troubleshooting
- OSMnx API: function names have changed across versions. If you encounter an error with OSMnx functions, check your `osmnx` version and update function calls (e.g., `geometries_from_place` vs `features_from_place`).
- CRS and distances: DBSCAN `eps` is in projected units (meters) because the script uses EPSG:3857 for distance calculations. If you change `hex_radius_m`, consider adjusting `eps`.
- Large areas: generating a dense hex grid over large administrative boundaries may create many cells and use a lot of memory. Consider limiting the grid to a buffered convex hull around your amenity points.
- Installing geopandas/fiona/shapely via pip can fail on some systems due to native dependencies (GDAL/PROJ). Use conda-forge for a smoother install.

