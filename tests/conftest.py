"""
Pytest fixtures for hexanalysis tests.
"""

import pytest
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon, box


@pytest.fixture
def sample_boundary_gdf():
    """Create a simple square boundary for testing."""
    geometry = box(0, 0, 1000, 1000)
    return gpd.GeoDataFrame(
        {"name": ["Test Area"]},
        geometry=[geometry],
        crs="EPSG:3857",
    )


@pytest.fixture
def sample_amenities_gdf():
    """Create sample amenity points for testing."""
    points = [
        Point(100, 100),
        Point(200, 150),
        Point(150, 200),
        Point(500, 500),
        Point(510, 510),
        Point(520, 520),
        Point(800, 800),
    ]
    amenities = ["cafe", "cafe", "cafe", "school", "school", "restaurant", "hospital"]
    names = [f"Test {a}" for a in amenities]

    return gpd.GeoDataFrame(
        {"amenity": amenities, "name": names},
        geometry=points,
        crs="EPSG:3857",
    )


@pytest.fixture
def sample_hex_gdf():
    """Create a simple hex grid for testing."""
    from hexanalysis.hexgrid import make_hex_grid

    hexagons = make_hex_grid(0, 0, 1000, 1000, 200)
    gdf = gpd.GeoDataFrame({"geometry": hexagons}, crs="EPSG:3857")
    gdf["count"] = 0
    gdf["diversity"] = 0
    return gdf
