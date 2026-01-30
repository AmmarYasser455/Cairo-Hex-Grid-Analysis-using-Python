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

    def test_empty_cells_have_zero(self, sample_amenities_gdf, sample_hex_gdf):
        """Cells without amenities should have count=0."""
        result = aggregate_amenities(sample_amenities_gdf, sample_hex_gdf)
        # At least some cells should be empty given sparse points
        assert (result["count"] == 0).any()
