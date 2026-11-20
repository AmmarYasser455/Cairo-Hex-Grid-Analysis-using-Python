"""
Tests for analysis module.
"""

import numpy as np
import pytest
import geopandas as gpd
from shapely.geometry import Point

from hexanalysis.analysis import (
    normalize,
    compute_scores,
    detect_hotspots,
    aggregate_amenities,
)


class TestNormalize:
    """Tests for normalize function."""

    def test_midpoint(self):
        """Midpoint should normalize to 0.5."""
        assert normalize(50, 0, 100) == 0.5

    def test_minimum(self):
        """Minimum value should normalize to 0."""
        assert normalize(0, 0, 100) == 0.0

    def test_maximum(self):
        """Maximum value should normalize to 1."""
        assert normalize(100, 0, 100) == 1.0

    def test_equal_min_max(self):
        """Equal min/max should return 0."""
        assert normalize(50, 50, 50) == 0.0

    def test_nan_input(self):
        """NaN input should return 0."""
        assert normalize(np.nan, 0, 100) == 0.0

    def test_negative_range(self):
        """Should work with negative values."""
        assert normalize(-50, -100, 0) == 0.5


class TestComputeScores:
    """Tests for compute_scores function."""

    def test_adds_required_columns(self, sample_hex_gdf):
        """Should add all expected columns."""
        result = compute_scores(sample_hex_gdf)
        expected_cols = [
            "area_m2", "area_km2", "density_per_km2",
            "density_norm", "diversity_norm", "score"
        ]
        for col in expected_cols:
            assert col in result.columns

    def test_score_range(self, sample_hex_gdf):
        """Scores should be in [0, 1] range."""
        # Add some non-zero values
        sample_hex_gdf.loc[0, "count"] = 10
        sample_hex_gdf.loc[0, "diversity"] = 3
        sample_hex_gdf.loc[1, "count"] = 5
        sample_hex_gdf.loc[1, "diversity"] = 2

        result = compute_scores(sample_hex_gdf)
        assert result["score"].min() >= 0.0
        assert result["score"].max() <= 1.0

    def test_weights_must_sum_to_one(self, sample_hex_gdf):
        """Should raise error if weights don't sum to 1."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            compute_scores(sample_hex_gdf, density_weight=0.5, diversity_weight=0.3)

    @pytest.mark.parametrize("dw, vw", [(1.5, -0.5), (-0.2, 1.2)])
    def test_negative_weights_rejected(self, sample_hex_gdf, dw, vw):
        """Negative weights summing to 1 would give scores outside [0, 1]."""
        with pytest.raises(ValueError, match="non-negative"):
            compute_scores(sample_hex_gdf, density_weight=dw, diversity_weight=vw)

    def test_custom_weights(self, sample_hex_gdf):
        """Should apply custom weights correctly."""
        sample_hex_gdf.loc[0, "count"] = 10
        sample_hex_gdf.loc[0, "diversity"] = 5

        result_density = compute_scores(
            sample_hex_gdf, density_weight=1.0, diversity_weight=0.0
        )
        result_diversity = compute_scores(
            sample_hex_gdf, density_weight=0.0, diversity_weight=1.0
        )

        # With 100% density weight, score should equal density_norm
        assert np.isclose(
            result_density.loc[0, "score"],
            result_density.loc[0, "density_norm"],
        )


class TestDetectHotspotsGeometries:
    """detect_hotspots must tolerate missing and non-point geometries."""

    def test_none_and_empty_geometries_ignored(self):
        gdf = gpd.GeoDataFrame(
            {"amenity": ["cafe"] * 5},
            geometry=[Point(0, 0), Point(10, 0), Point(0, 10), None, Point()],
            crs=3857,
        )
        result = detect_hotspots(gdf, eps=50, min_samples=3)
        assert len(result) == 1
        assert result["size"].iloc[0] == 3

    def test_polygons_use_centroid(self):
        from shapely.geometry import box
        gdf = gpd.GeoDataFrame(
            {"amenity": ["cafe"] * 3},
            geometry=[box(0, 0, 10, 10), Point(10, 0), Point(0, 10)],
            crs=3857,
        )
        result = detect_hotspots(gdf, eps=50, min_samples=3)
        assert len(result) == 1
        assert result["size"].iloc[0] == 3
        assert result.crs == gdf.crs


class TestDetectHotspots:
    """Tests for detect_hotspots function."""

    def test_finds_clusters(self, sample_amenities_gdf):
        """Should find clusters of cafes."""
        result = detect_hotspots(
            sample_amenities_gdf,
            amenity_type="cafe",
            eps=100,
            min_samples=2,
        )
        assert len(result) >= 1
        assert "cluster" in result.columns
        assert "size" in result.columns

    def test_empty_when_no_amenity_type(self, sample_amenities_gdf):
        """Should return empty if amenity type not present."""
        result = detect_hotspots(
            sample_amenities_gdf,
            amenity_type="bank",
            eps=100,
            min_samples=2,
        )
        assert len(result) == 0

    def test_empty_when_too_few_points(self, sample_amenities_gdf):
        """Should return empty if not enough points for clustering."""
        result = detect_hotspots(
            sample_amenities_gdf,
            amenity_type="hospital",
            eps=100,
            min_samples=5,
        )
        assert len(result) == 0

    def test_preserves_crs(self, sample_amenities_gdf):
        """Result should have same CRS as input."""
        result = detect_hotspots(
            sample_amenities_gdf,
            amenity_type="cafe",
            eps=100,
            min_samples=2,
        )
        if len(result) > 0:
            assert result.crs == sample_amenities_gdf.crs


class TestAggregateAmenities:
    """Tests for aggregate_amenities function."""

    def test_adds_count_and_diversity(self, sample_amenities_gdf, sample_hex_gdf):
        """Should add count and diversity columns."""
        result = aggregate_amenities(sample_amenities_gdf, sample_hex_gdf)
        assert "count" in result.columns
        assert "diversity" in result.columns

    def test_counts_are_integers(self, sample_amenities_gdf, sample_hex_gdf):
        """Counts should be integer values."""
        result = aggregate_amenities(sample_amenities_gdf, sample_hex_gdf)
        assert result["count"].dtype in [np.int64, np.int32, int]
        assert result["diversity"].dtype in [np.int64, np.int32, int]

    def test_empty_amenities(self, sample_amenities_gdf, sample_hex_gdf):
        """No amenities at all should give zero counts, not an error."""
        result = aggregate_amenities(sample_amenities_gdf.iloc[0:0], sample_hex_gdf)
        assert (result["count"] == 0).all()
        assert (result["diversity"] == 0).all()

    def test_named_and_non_default_index(self, sample_amenities_gdf, sample_hex_gdf):
        """Hex grids with a named, non-range index are handled."""
        hexes = sample_hex_gdf.copy()
        hexes.index = [f"h{i}" for i in range(len(hexes))]
        hexes.index.name = "hex_id"
        result = aggregate_amenities(sample_amenities_gdf, hexes)
        assert result["count"].sum() == 7
        assert list(result.index) == list(hexes.index)

    def test_existing_index_right_column(self, sample_amenities_gdf, sample_hex_gdf):
        """Input with a stray 'index_right' column does not break the join."""
        amenities = sample_amenities_gdf.copy()
        amenities["index_right"] = 0
        result = aggregate_amenities(amenities, sample_hex_gdf)
        assert result["count"].sum() == 7

    def test_points_on_shared_edge_counted_once(self, sample_hex_gdf):
        """A point on a cell boundary is counted exactly once."""
        edge = sample_hex_gdf.geometry.iloc[0].exterior.coords[0]
        pts = gpd.GeoDataFrame(
            {"amenity": ["cafe"]}, geometry=[Point(edge)], crs=sample_hex_gdf.crs
        )
        result = aggregate_amenities(pts, sample_hex_gdf)
        assert result["count"].sum() == 1

    def test_empty_cells_have_zero(self, sample_amenities_gdf, sample_hex_gdf):
        """Cells without amenities should have count=0."""
        result = aggregate_amenities(sample_amenities_gdf, sample_hex_gdf)
        # At least some cells should be empty given sparse points
        assert (result["count"] == 0).any()


class TestCrsHandling:
    # Tahrir Square, Cairo (lon, lat)
    LON, LAT = 31.2357, 30.0444

    def test_aggregate_reprojects_mismatched_crs(self):
        from shapely.geometry import box

        pts = gpd.GeoDataFrame(
            {"amenity": ["cafe"]},
            geometry=[Point(self.LON, self.LAT)],
            crs="EPSG:4326",
        )
        x, y = pts.to_crs("EPSG:32636").geometry.iloc[0].coords[0]
        cells = gpd.GeoDataFrame(
            geometry=[box(x - 100, y - 100, x + 100, y + 100)], crs="EPSG:32636"
        )
        out = aggregate_amenities(pts, cells)
        assert out["count"].tolist() == [1]
        assert out.crs == cells.crs

    def test_compute_scores_rejects_geographic_crs(self):
        from shapely.geometry import box

        gdf = gpd.GeoDataFrame(
            {"count": [1], "diversity": [1]},
            geometry=[box(31.2, 30.0, 31.3, 30.1)],
            crs="EPSG:4326",
        )
        with pytest.raises(ValueError, match="projected"):
            compute_scores(gdf)

    def test_detect_hotspots_rejects_geographic_crs(self):
        gdf = gpd.GeoDataFrame(
            {"amenity": ["cafe"] * 3},
            geometry=[Point(self.LON, self.LAT)] * 3,
            crs="EPSG:4326",
        )
        with pytest.raises(ValueError, match="projected"):
            detect_hotspots(gdf)

    def test_compute_scores_rejects_non_metre_projected_crs(self):
        from shapely.geometry import box

        # EPSG:2263 is NY State Plane in US survey feet
        gdf = gpd.GeoDataFrame(
            {"count": [1], "diversity": [1]},
            geometry=[box(0, 0, 1000, 1000)],
            crs="EPSG:2263",
        )
        with pytest.raises(ValueError, match="metre"):
            compute_scores(gdf)

    def test_detect_hotspots_rejects_non_metre_projected_crs(self):
        gdf = gpd.GeoDataFrame(
            {"amenity": ["cafe"] * 3},
            geometry=[Point(0, 0)] * 3,
            crs="EPSG:2263",
        )
        with pytest.raises(ValueError, match="metre"):
            detect_hotspots(gdf)


def _cell(crs):
    from shapely.geometry import box

    return gpd.GeoDataFrame(
        {"count": [1], "diversity": [1]}, geometry=[box(0, 0, 10, 10)], crs=crs
    )


def _pts(crs):
    return gpd.GeoDataFrame(
        {"amenity": ["cafe"] * 3}, geometry=[Point(0, 0)] * 3, crs=crs
    )


_GOOD_PTS = _pts("EPSG:3857")
_GOOD_CELL = _cell("EPSG:3857")


@pytest.mark.parametrize(
    "call, exc, match",
    [
        # missing CRS on each input
        (lambda: compute_scores(_cell(None)), ValueError, "CRS"),
        (lambda: detect_hotspots(_pts(None)), ValueError, "CRS"),
        (lambda: aggregate_amenities(_pts(None), _GOOD_CELL), ValueError, "CRS"),
        (lambda: aggregate_amenities(_GOOD_PTS, _cell(None)), ValueError, "CRS"),
        # geographic (degrees)
        (lambda: compute_scores(_cell("EPSG:4326")), ValueError, "geographic"),
        (lambda: detect_hotspots(_pts("EPSG:4326")), ValueError, "geographic"),
        # geocentric: metre axes but not a projected CRS
        (lambda: compute_scores(_cell("EPSG:4978")), ValueError, "non-projected"),
        (lambda: detect_hotspots(_pts("EPSG:4978")), ValueError, "non-projected"),
        # projected in US survey feet
        (lambda: compute_scores(_cell("EPSG:2263")), ValueError, "metre"),
        (lambda: detect_hotspots(_pts("EPSG:2263")), ValueError, "metre"),
        # wrong input types
        (lambda: compute_scores(None), TypeError, "GeoDataFrame"),
        (lambda: compute_scores({"count": [1]}), TypeError, "GeoDataFrame"),
        (lambda: detect_hotspots("cafes.geojson"), TypeError, "GeoDataFrame"),
        (lambda: aggregate_amenities(None, _GOOD_CELL), TypeError, "GeoDataFrame"),
        (lambda: aggregate_amenities(_GOOD_PTS, [1, 2]), TypeError, "GeoDataFrame"),
    ],
)
def test_invalid_inputs_rejected(call, exc, match):
    with pytest.raises(exc, match=match):
        call()


def test_utm_metre_crs_accepted():
    # UTM 36N (EPSG:32636) covers Cairo and is in metres
    out = compute_scores(_cell("EPSG:32636"))
    assert out["area_m2"].iloc[0] == pytest.approx(100.0)
