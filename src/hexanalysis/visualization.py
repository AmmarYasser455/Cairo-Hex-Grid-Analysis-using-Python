"""
Map visualization utilities using Folium.

This module provides functions for creating interactive maps
that display hex grids, amenities, and hotspots.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import folium
import branca
from folium.plugins import HeatMap, MarkerCluster

if TYPE_CHECKING:
    import geopandas as gpd


# Color mapping for different amenity types
AMENITY_COLORS = {
    "school": "blue",
    "university": "darkblue",
    "hospital": "green",
    "clinic": "lightgreen",
    "cafe": "brown",
    "restaurant": "orange",
    "bank": "purple",
    "supermarket": "red",
    "pharmacy": "pink",
}


def create_map(
    hex_gdf: "gpd.GeoDataFrame",
    amenities_gdf: "gpd.GeoDataFrame",
    hotspots_gdf: "gpd.GeoDataFrame",
    area_gdf: "gpd.GeoDataFrame",
    zoom_start: int = 12,
) -> folium.Map:
    """
    Create an interactive Folium map with hex grid and amenities.

    Args:
        hex_gdf: GeoDataFrame of hex cells with 'score', 'count', etc.
            Should be in WGS84 (EPSG:4326).
        amenities_gdf: GeoDataFrame with amenity points in WGS84.
        hotspots_gdf: GeoDataFrame with hotspot centroids in WGS84.
        area_gdf: GeoDataFrame with area boundary in WGS84.
        zoom_start: Initial zoom level (default 12).

    Returns:
        Folium Map object with layers for hex grid, heatmap,
        amenity markers, hotspots, and area boundary.
    """
    # Calculate map center
    center_point = area_gdf.geometry.centroid.iloc[0]
    center = [center_point.y, center_point.x]

    # Create base map
    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles="CartoDB positron",
    )

    # Add amenity heatmap
    _add_heatmap(m, amenities_gdf)

    # Add hex grid with colormap
    _add_hex_grid(m, hex_gdf)

    # Add amenity markers
    _add_amenity_markers(m, amenities_gdf)

    # Add hotspot markers
    _add_hotspot_markers(m, hotspots_gdf)

    # Add area boundary
    _add_boundary(m, area_gdf)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    return m


def _add_heatmap(m: folium.Map, amenities_gdf: "gpd.GeoDataFrame") -> None:
    """Add heatmap layer from amenity points."""
    points = [[pt.y, pt.x] for pt in amenities_gdf.geometry]
    if points:
        HeatMap(
            points,
            radius=10,
            blur=15,
            name="Amenities Heatmap",
        ).add_to(m)


def _add_hex_grid(m: folium.Map, hex_gdf: "gpd.GeoDataFrame") -> None:
    """Add hex grid layer with score-based coloring."""
    if hex_gdf.empty:
        return

    # Create colormap
    colormap = branca.colormap.linear.YlOrRd_09.scale(
        hex_gdf["score"].min(),
        hex_gdf["score"].max(),
    )
    colormap.caption = "Service Score (density + diversity)"
    colormap.add_to(m)

    # Add GeoJSON layer
    hex_geojson = folium.GeoJson(
        hex_gdf,
        name="Hex Grid (score)",
        style_function=lambda feat: {
            "fillColor": colormap(feat["properties"]["score"]),
            "color": "#444444",
            "weight": 0.5,
            "fillOpacity": 0.7 if feat["properties"]["count"] > 0 else 0.1,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["count", "diversity", "density_per_km2", "score"],
            aliases=["Count", "Diversity", "Density / km²", "Score"],
            localize=True,
        ),
    )
    hex_geojson.add_to(m)


def _add_amenity_markers(m: folium.Map, amenities_gdf: "gpd.GeoDataFrame") -> None:
    """Add clustered amenity markers."""
    if amenities_gdf.empty:
        return

    mc = MarkerCluster(name="Amenities (clustered)").add_to(m)

    for _, row in amenities_gdf.iterrows():
        amenity_type = row.get("amenity", "")
        name = row.get("name", "(no name)")
        popup_text = f"{amenity_type} - {name}"

        color = AMENITY_COLORS.get(amenity_type, "gray")

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=4,
            popup=popup_text,
            color=color,
            fill=True,
        ).add_to(mc)


def _add_hotspot_markers(m: folium.Map, hotspots_gdf: "gpd.GeoDataFrame") -> None:
    """Add hotspot cluster markers."""
    if hotspots_gdf.empty:
        return

    for _, row in hotspots_gdf.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=8 + int(row["size"]),
            color="red",
            fill=True,
            fill_opacity=0.9,
            popup=f"Hotspot cluster #{int(row['cluster'])} (size={int(row['size'])})",
        ).add_to(m)


def _add_boundary(m: folium.Map, area_gdf: "gpd.GeoDataFrame") -> None:
    """Add area boundary outline."""
    folium.GeoJson(
        area_gdf,
        name="Area Boundary",
        style_function=lambda x: {
            "color": "black",
            "weight": 2,
            "fillOpacity": 0,
        },
    ).add_to(m)
