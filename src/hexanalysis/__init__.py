"""
HexAnalysis - Hexagonal grid geospatial analysis package.

Provides tools for generating hex grids, aggregating OSM amenities,
computing service scores, and detecting hotspots.
"""

__version__ = "0.2.0"
__author__ = "Ammar Yasser Abdalazim"

from .config import Config
from .hexgrid import make_hexagon, make_hex_grid, create_hex_grid_gdf
from .analysis import normalize, compute_scores, detect_hotspots, aggregate_amenities
from .osm import fetch_area, fetch_amenities
from .visualization import create_map

__all__ = [
    "Config",
    "make_hexagon",
    "make_hex_grid",
    "create_hex_grid_gdf",
    "normalize",
    "compute_scores",
    "detect_hotspots",
    "aggregate_amenities",
    "fetch_area",
    "fetch_amenities",
    "create_map",
]
