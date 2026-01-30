"""
Analysis utilities for hex grid geospatial analysis.

This module provides functions for normalizing values, computing
service scores, and detecting spatial hotspots using DBSCAN clustering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import geopandas as gpd
from sklearn.cluster import DBSCAN

if TYPE_CHECKING:
    from numpy.typing import NDArray


def normalize(value: float, min_val: float, max_val: float) -> float:
    """
    Normalize a value to [0, 1] range using min-max scaling.

    Args:
        value: Value to normalize.
        min_val: Minimum value in the range.
        max_val: Maximum value in the range.

    Returns:
        Normalized value between 0 and 1, or 0 if min equals max.

    Example:
        >>> normalize(50, 0, 100)
        0.5
        >>> normalize(25, 0, 100)
        0.25
    """
    if np.isnan(value) or max_val == min_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


def compute_scores(
    hex_gdf: gpd.GeoDataFrame,
    density_weight: float = 0.65,
    diversity_weight: float = 0.35,
) -> gpd.GeoDataFrame:
    """
    Compute service scores for hex cells based on density and diversity.

    The function adds normalized density, normalized diversity, and a
    weighted composite score to the GeoDataFrame.

    Args:
        hex_gdf: GeoDataFrame with 'count', 'diversity', and geometry columns.
        density_weight: Weight for density in score (default 0.65).
        diversity_weight: Weight for diversity in score (default 0.35).

    Returns:
        GeoDataFrame with added columns: area_m2, area_km2, density_per_km2,
        density_norm, diversity_norm, score.

    Raises:
        ValueError: If weights don't sum to 1.0 (within tolerance).
    """
    if not np.isclose(density_weight + diversity_weight, 1.0):
        raise ValueError(
            f"Weights must sum to 1.0, got {density_weight + diversity_weight}"
        )

    gdf = hex_gdf.copy()

    # Compute area and density
    gdf["area_m2"] = gdf.geometry.area
    gdf["area_km2"] = gdf["area_m2"] / 1e6
    gdf["density_per_km2"] = gdf["count"] / gdf["area_km2"].replace({0: np.nan})

    # Get min/max for normalization
    d_min = gdf["density_per_km2"].min(skipna=True)
    d_max = gdf["density_per_km2"].max(skipna=True)
    v_min = gdf["diversity"].min()
    v_max = gdf["diversity"].max()

    # Normalize values
    gdf["density_norm"] = gdf["density_per_km2"].apply(
        lambda x: normalize(x, d_min, d_max)
    )
    gdf["diversity_norm"] = gdf["diversity"].apply(
        lambda x: normalize(x, v_min, v_max)
    )

    # Compute weighted score
    gdf["score"] = (
        density_weight * gdf["density_norm"]
        + diversity_weight * gdf["diversity_norm"]
    )

    return gdf


def detect_hotspots(
    amenities_gdf: gpd.GeoDataFrame,
    amenity_type: str = "cafe",
    eps: float = 200.0,
    min_samples: int = 3,
) -> gpd.GeoDataFrame:
    """
    Detect spatial hotspots using DBSCAN clustering.

    Args:
        amenities_gdf: GeoDataFrame with amenity points (projected CRS).
        amenity_type: Type of amenity to cluster (default "cafe").
        eps: Maximum distance between points in a cluster (meters).
        min_samples: Minimum points to form a cluster.

    Returns:
        GeoDataFrame with cluster centroids including 'cluster' and 'size'.
        Empty GeoDataFrame if no clusters found.

    Note:
        Input GeoDataFrame should be in a projected CRS (e.g., EPSG:3857)
        for meaningful distance calculations.
    """
    # Filter to specified amenity type
    filtered = amenities_gdf[amenities_gdf["amenity"] == amenity_type].copy()

    if len(filtered) < min_samples:
        return gpd.GeoDataFrame(
            columns=["geometry", "cluster", "size"],
            crs=amenities_gdf.crs,
        )

    # Extract coordinates for DBSCAN
    coords: NDArray[np.float64] = np.array(
        [(p.x, p.y) for p in filtered.geometry]
    )

    # Run DBSCAN
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    filtered["cluster"] = db.labels_

    # Build cluster centroids
    clusters = []
    for label in filtered["cluster"].unique():
        if label < 0:  # Skip noise points
            continue
        members = filtered[filtered["cluster"] == label]
        centroid = members.geometry.union_all().centroid
        clusters.append({
            "geometry": centroid,
            "cluster": int(label),
            "size": len(members),
        })

    if not clusters:
        return gpd.GeoDataFrame(
            columns=["geometry", "cluster", "size"],
            crs=amenities_gdf.crs,
        )

    return gpd.GeoDataFrame(clusters, crs=amenities_gdf.crs)


def aggregate_amenities(
    amenities_gdf: gpd.GeoDataFrame,
    hex_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Aggregate amenity counts and diversity per hex cell.

    Args:
        amenities_gdf: GeoDataFrame with amenity points (same CRS as hex_gdf).
        hex_gdf: GeoDataFrame with hex polygons.

    Returns:
        GeoDataFrame with 'count' and 'diversity' columns added.
    """
    gdf = hex_gdf.copy()

    # Spatial join
    joined = gpd.sjoin(amenities_gdf, gdf, how="inner", predicate="within")

    # Aggregate counts
    counts = joined.groupby("index_right").size().rename("count")
    diversity = joined.groupby("index_right")["amenity"].nunique().rename("diversity")

    # Map to hex grid
    gdf["count"] = gdf.index.map(counts).fillna(0).astype(int)
    gdf["diversity"] = gdf.index.map(diversity).fillna(0).astype(int)

    return gdf
