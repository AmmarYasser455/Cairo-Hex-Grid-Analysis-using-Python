"""
Hexagonal grid generation utilities.

This module provides functions for creating hexagonal grids
in projected coordinate systems for spatial analysis.
"""

from __future__ import annotations

import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon


def make_hexagon(center_x: float, center_y: float, radius: float) -> Polygon:
    """
    Create a flat-top hexagon polygon.

    Args:
        center_x: X coordinate of hexagon center.
        center_y: Y coordinate of hexagon center.
        radius: Distance from center to vertex (apothem).

    Returns:
        A shapely Polygon representing the hexagon.

    Example:
        >>> hex_poly = make_hexagon(0, 0, 100)
        >>> hex_poly.area  # Approximately 25980.76 for r=100
    """
    angles = np.linspace(0, 2 * np.pi, 7)[:-1]
    points = [
        (center_x + radius * np.cos(angle), center_y + radius * np.sin(angle))
        for angle in angles
    ]
    return Polygon(points)


def make_hex_grid(
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
    radius: float,
) -> list[Polygon]:
    """
    Generate a hexagonal grid covering a bounding box.

    Creates flat-top hexagons with proper offset pattern for
    tessellation without gaps.

    Args:
        minx: Minimum X coordinate of bounding box.
        miny: Minimum Y coordinate of bounding box.
        maxx: Maximum X coordinate of bounding box.
        maxy: Maximum Y coordinate of bounding box.
        radius: Hexagon radius in same units as coordinates.

    Returns:
        List of shapely Polygon hexagons covering the area.

    Note:
        The bounding box should be in a projected CRS (meters)
        for meaningful radius values.

    Example:
        >>> hexagons = make_hex_grid(0, 0, 1000, 1000, 100)
        >>> len(hexagons) > 0
        True
    """
    # Horizontal and vertical spacing for flat-top hexagons
    dx = 1.5 * radius
    dy = np.sqrt(3) * radius

    hexagons: list[Polygon] = []
    row = 0
    y = miny - dy

    while y < maxy + dy:
        # Offset every other row for proper tessellation
        x_offset = 0.75 * radius if row % 2 == 1 else 0
        x = minx - dx

        while x < maxx + dx:
            hexagon = make_hexagon(x + x_offset, y, radius)
            hexagons.append(hexagon)
            x += dx

        y += dy
        row += 1

    return hexagons


def create_hex_grid_gdf(
    boundary_gdf: gpd.GeoDataFrame,
    radius: float,
    crs: str = "EPSG:3857",
) -> gpd.GeoDataFrame:
    """
    Create a hexagonal grid clipped to a boundary.

    Args:
        boundary_gdf: GeoDataFrame with boundary geometry.
        radius: Hexagon radius in meters.
        crs: Projected CRS to use for grid generation.

    Returns:
        GeoDataFrame of hexagons that intersect the boundary.
    """
    # Project to meters
    boundary_proj = boundary_gdf.to_crs(crs)
    boundary_geom = boundary_proj.geometry.union_all()
    minx, miny, maxx, maxy = boundary_geom.bounds

    # Generate hexagons
    hex_polys = make_hex_grid(minx, miny, maxx, maxy, radius)
    hex_gdf = gpd.GeoDataFrame({"geometry": hex_polys}, crs=crs)

    # Keep only hexagons that intersect the boundary
    hex_gdf = hex_gdf[hex_gdf.intersects(boundary_geom)].copy()
    hex_gdf = hex_gdf.reset_index(drop=True)

    return hex_gdf
