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

    def test_tessellates_exactly(self):
        """Hexagons must neither overlap nor leave gaps inside the bbox."""
        from shapely.geometry import box
        from shapely.ops import unary_union

        hexagons = make_hex_grid(0, 0, 500, 500, 100)
        union = unary_union(hexagons)
        total_area = sum(h.area for h in hexagons)
        assert np.isclose(total_area, union.area, rtol=1e-6)
        bbox = box(0, 0, 500, 500)
        assert np.isclose(union.intersection(bbox).area, bbox.area, rtol=1e-6)

    @pytest.mark.parametrize("radius", [0, -5])
    def test_non_positive_radius_raises(self, radius):
        """A non-positive radius must fail instead of looping forever."""
        with pytest.raises(ValueError):
            make_hex_grid(0, 0, 500, 500, radius)

    def test_larger_area_more_hexagons(self):
        """Larger bounding boxes should produce more hexagons."""
        small = make_hex_grid(0, 0, 500, 500, 100)
        large = make_hex_grid(0, 0, 2000, 2000, 100)
        assert len(large) > len(small)


class TestAutoCrs:
    """create_hex_grid_gdf(crs="auto") uses the local UTM zone."""

    @staticmethod
    def _tahrir():
        import geopandas as gpd
        from shapely.geometry import box

        # ~1 km box around Tahrir Square, Cairo (x=lon, y=lat)
        return gpd.GeoDataFrame(
            geometry=[box(31.230, 30.039, 31.240, 30.048)], crs="EPSG:4326"
        )

    def test_auto_selects_utm_36n(self):
        result = create_hex_grid_gdf(self._tahrir(), radius=200, crs="auto")
        assert result.crs.to_epsg() == 32636

    def test_auto_radius_is_ground_metres(self):
        auto = create_hex_grid_gdf(self._tahrir(), radius=200, crs="auto")
        merc = create_hex_grid_gdf(self._tahrir(), radius=200)
        expected = 3 * np.sqrt(3) / 2 * 200**2
        assert np.isclose(auto.geometry.area.iloc[0], expected, rtol=1e-6)
        # Web Mercator inflates the nominal area; true ground area is smaller
        ground = merc.to_crs(auto.crs).geometry.area.iloc[0]
        assert ground < 0.8 * expected

    def test_geographic_crs_rejected(self):
        with pytest.raises(ValueError):
            create_hex_grid_gdf(self._tahrir(), radius=200, crs="EPSG:4326")

    def test_non_metre_projected_crs_rejected(self):
        # NAD83 / California zone 5 (ftUS), EPSG:2229; Los Angeles boundary
        import geopandas as gpd
        from shapely.geometry import box

        la = gpd.GeoDataFrame(
            geometry=[box(-118.26, 34.04, -118.24, 34.06)], crs="EPSG:4326"
        )
        with pytest.raises(ValueError, match="metre"):
            create_hex_grid_gdf(la, radius=400, crs="EPSG:2229")

    def test_missing_boundary_crs_rejected(self, sample_boundary_gdf):
        no_crs = sample_boundary_gdf.set_crs(None, allow_override=True)
        with pytest.raises(ValueError):
            create_hex_grid_gdf(no_crs, 100)


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


class TestInputValidation:
    def test_non_finite_radius_rejected(self):
        for r in (float("nan"), float("inf"), -1.0, 0):
            with pytest.raises(ValueError, match="radius"):
                make_hex_grid(0, 0, 1000, 1000, r)

    def test_non_finite_bbox_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            make_hex_grid(float("nan"), 0, 1000, 1000, 100)

    def test_empty_or_null_boundary_rejected(self):
        import geopandas as gpd

        for geoms in ([], [None], [Polygon()]):
            gdf = gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326")
            with pytest.raises(ValueError, match="no non-empty geometry"):
                create_hex_grid_gdf(gdf, radius=400)

    def test_null_rows_ignored_next_to_valid_boundary(self):
        import geopandas as gpd
        from shapely.geometry import box

        # Real extent around central Cairo (lon 31.23-31.25, lat 30.04-30.06)
        gdf = gpd.GeoDataFrame(
            geometry=[None, box(31.23, 30.04, 31.25, 30.06)], crs="EPSG:4326"
        )
        result = create_hex_grid_gdf(gdf, radius=400, crs="auto")
        assert len(result) > 0
        assert result.crs.to_epsg() == 32636

    def test_duplicate_index_labels_do_not_expand_input(self):
        import geopandas as gpd
        from shapely.geometry import box

        gdf = gpd.GeoDataFrame(
            geometry=[None, box(31.23, 30.04, 31.25, 30.06), box(31.23, 30.04, 31.25, 30.06)],
            index=[0, 0, 0],
            crs="EPSG:4326",
        )
        single = gpd.GeoDataFrame(
            geometry=[box(31.23, 30.04, 31.25, 30.06)], crs="EPSG:4326"
        )
        a = create_hex_grid_gdf(gdf, radius=400, crs="auto")
        b = create_hex_grid_gdf(single, radius=400, crs="auto")
        assert len(a) == len(b)
