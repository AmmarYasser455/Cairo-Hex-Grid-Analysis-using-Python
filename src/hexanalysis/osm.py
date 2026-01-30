"""
OpenStreetMap data fetching utilities.

This module provides functions for downloading area boundaries
and amenity data from OpenStreetMap using OSMnx.
"""

from __future__ import annotations

import geopandas as gpd
import osmnx as ox


def fetch_area(place_name: str) -> gpd.GeoDataFrame:
    """
    Fetch the administrative boundary of a place.

    Args:
        place_name: Name of place to geocode (e.g., "Cairo, Egypt").

    Returns:
        GeoDataFrame with the area boundary geometry.

    Raises:
        ValueError: If place cannot be geocoded.

    Example:
        >>> gdf = fetch_area("Cairo, Egypt")
        >>> gdf.crs.to_epsg()
        4326
    """
    try:
        return ox.geocode_to_gdf(place_name)
    except Exception as e:
        raise ValueError(f"Could not geocode '{place_name}': {e}") from e


def fetch_amenities(
    place_name: str,
    amenity_types: list[str] | None = None,
) -> gpd.GeoDataFrame:
    """
    Fetch OSM amenities for a place, filtered by type.

    Downloads all amenities and filters to specified types.
    Polygons are converted to centroids for point-based analysis.

    Args:
        place_name: Name of place to query.
        amenity_types: List of amenity types to include. If None, includes:
            school, university, hospital, clinic, cafe, restaurant,
            bank, supermarket, pharmacy.

    Returns:
        GeoDataFrame with point geometries in WGS84 (EPSG:4326).

    Note:
        Requires internet connection to query OSM Overpass API.
    """
    if amenity_types is None:
        amenity_types = [
            "school",
            "university",
            "hospital",
            "clinic",
            "cafe",
            "restaurant",
            "bank",
            "supermarket",
            "pharmacy",
        ]

    # Fetch all amenities
    tags = {"amenity": True}
    raw = ox.features_from_place(place_name, tags)

    # Remove empty geometries
    raw = raw[~raw.geometry.is_empty].copy()

    # Convert to centroids (for polygons like building footprints)
    raw["geometry"] = raw.geometry.centroid
    raw = raw.set_geometry("geometry").to_crs(epsg=4326)

    # Filter to types of interest
    filtered = raw[raw["amenity"].isin(amenity_types)].copy()
    filtered = filtered.reset_index(drop=True)

    return filtered
