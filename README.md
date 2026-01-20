# Cairo Service Accessibility Analysis (Hex Grid + Hotspots)

## Project Overview
This project analyzes the distribution of services in Cairo using Python and GIS. 
It generates a hex-grid map to evaluate density and diversity of amenities like schools, cafes, hospitals, etc., 
and identifies service hotspots using clustering.

## Tools & Libraries
- Python: geopandas, osmnx, folium, shapely, scikit-learn, numpy, pandas, branca
- Data source: OpenStreetMap
- GIS concepts: spatial join, density/diversity analysis, hex-grid analysis

## Features
- Interactive Folium map (`cairo_hex_map.html`) with layers and tooltips.
- Hex grid GeoJSON (`cairo_hexgrid.geojson`) for spatial analysis.
- Hotspot GeoJSON (`hotspots.geojson`) showing clusters of amenities.
- Custom score combining density and diversity for each hex cell.

## How to Run
1. Open the project folder.
2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
