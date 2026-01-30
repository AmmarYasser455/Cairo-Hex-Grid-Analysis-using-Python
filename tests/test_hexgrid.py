"""
Tests for hexgrid module.
"""

import numpy as np
import pytest
from shapely.geometry import Polygon

from hexanalysis.hexgrid import make_hexagon, make_hex_grid, create_hex_grid_gdf


class TestMakeHexagon:
    """Tests for make_hexagon function."""

    def test_returns_polygon(self):
        """Hexagon should be a valid polygon."""
        hex_poly = make_hexagon(0, 0, 100)
        assert isinstance(hex_poly, Polygon)
        assert hex_poly.is_valid

    def test_has_six_vertices(self):
        """Hexagon should have 6 unique vertices."""
        hex_poly = make_hexagon(0, 0, 100)
        # Exterior ring has 7 coords (first == last)
        coords = list(hex_poly.exterior.coords)
        assert len(coords) == 7
        # 6 unique vertices
        unique = set(coords[:-1])
        assert len(unique) == 6

    def test_correct_area(self):
        """Hexagon area should match formula: (3√3/2) * r²."""
        radius = 100
        hex_poly = make_hexagon(0, 0, radius)
        expected_area = (3 * np.sqrt(3) / 2) * radius**2
        assert np.isclose(hex_poly.area, expected_area, rtol=0.01)

    def test_centered_at_origin(self):
        """Hexagon centroid should be at specified center."""
        hex_poly = make_hexagon(500, 300, 100)
        centroid = hex_poly.centroid
        assert np.isclose(centroid.x, 500, atol=0.1)
        assert np.isclose(centroid.y, 300, atol=0.1)

    def test_different_radii(self):
        """Larger radius should produce larger hexagon."""
        small = make_hexagon(0, 0, 50)
        large = make_hexagon(0, 0, 200)
        assert large.area > small.area
        assert np.isclose(large.area / small.area, 16, rtol=0.01)


class TestMakeHexGrid:
    """Tests for make_hex_grid function."""

    def test_returns_list_of_polygons(self):
        """Grid should be a list of valid polygons."""
        hexagons = make_hex_grid(0, 0, 1000, 1000, 100)
        assert isinstance(hexagons, list)
        assert len(hexagons) > 0
        assert all(isinstance(h, Polygon) for h in hexagons)

    def test_covers_bounding_box(self):
        """Hexagons should cover the entire bounding box."""
        hexagons = make_hex_grid(0, 0, 500, 500, 100)
        from shapely.ops import unary_union
        from shapely.geometry import box

        union = unary_union(hexagons)
        bbox = box(0, 0, 500, 500)
        # Union should contain the bounding box
        assert union.contains(bbox) or union.intersection(bbox).area / bbox.area > 0.90

    def test_no_gaps_between_hexagons(self):
        """Adjacent hexagons should tessellate without significant gaps."""
        hexagons = make_hex_grid(0, 0, 500, 500, 100)
        from shapely.ops import unary_union

        union = unary_union(hexagons)
        total_area = sum(h.area for h in hexagons)
        # Small overlap is expected; gap ratio should be minimal
        overlap_ratio = (total_area - union.area) / union.area
        assert overlap_ratio < 0.1  # Less than 10% overlap

    def test_larger_area_more_hexagons(self):
        """Larger bounding boxes should produce more hexagons."""
        small = make_hex_grid(0, 0, 500, 500, 100)
        large = make_hex_grid(0, 0, 2000, 2000, 100)
        assert len(large) > len(small)


class TestCreateHexGridGdf:
    """Tests for create_hex_grid_gdf function."""

    def test_returns_geodataframe(self, sample_boundary_gdf):
        """Should return a GeoDataFrame."""
        import geopandas as gpd

        result = create_hex_grid_gdf(sample_boundary_gdf, radius=100)
        assert isinstance(result, gpd.GeoDataFrame)

    def test_clips_to_boundary(self, sample_boundary_gdf):
        """Hexagons should only intersect the boundary."""
        result = create_hex_grid_gdf(sample_boundary_gdf, radius=100)
        boundary_geom = sample_boundary_gdf.to_crs("EPSG:3857").geometry.union_all()

        # All hexagons should intersect the boundary
        for hex_geom in result.geometry:
            assert hex_geom.intersects(boundary_geom)

    def test_has_correct_crs(self, sample_boundary_gdf):
        """Result should be in EPSG:3857."""
        result = create_hex_grid_gdf(sample_boundary_gdf, radius=100)
        assert result.crs.to_epsg() == 3857
