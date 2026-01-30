"""
Command-line interface for hex grid analysis.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config


def main() -> int:
    """Run hex grid analysis from command line."""
    parser = argparse.ArgumentParser(
        prog="hexanalysis",
        description="Hexagonal grid analysis of urban amenities",
    )
    parser.add_argument(
        "--place",
        default="Cairo, Egypt",
        help="Place name to analyze (default: 'Cairo, Egypt')",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=400.0,
        help="Hex radius in meters (default: 400)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory (default: 'output')",
    )
    parser.add_argument(
        "--dbscan-eps",
        type=float,
        default=200.0,
        help="DBSCAN epsilon distance in meters (default: 200)",
    )
    parser.add_argument(
        "--dbscan-min-samples",
        type=int,
        default=3,
        help="DBSCAN minimum samples per cluster (default: 3)",
    )

    args = parser.parse_args()

    # Create config
    config = Config(
        place_name=args.place,
        hex_radius_m=args.radius,
        output_folder=args.output,
        dbscan_eps=args.dbscan_eps,
        dbscan_min_samples=args.dbscan_min_samples,
    )

    # Run analysis
    try:
        run_analysis(config)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def run_analysis(config: Config) -> None:
    """
    Execute the full hex grid analysis pipeline.

    Args:
        config: Configuration object with analysis parameters.
    """
    # Import here to avoid slow imports when just showing help
    from .osm import fetch_area, fetch_amenities
    from .hexgrid import create_hex_grid_gdf
    from .analysis import aggregate_amenities, compute_scores, detect_hotspots
    from .visualization import create_map

    print(f"1) Downloading OSM data for: {config.place_name}")
    area_gdf = fetch_area(config.place_name)
    amenities = fetch_amenities(config.place_name, config.amenity_types)
    print(f"   → Found {len(amenities)} amenities of interest")

    print("2) Building hex grid (projected meters)...")
    hex_gdf = create_hex_grid_gdf(area_gdf, config.hex_radius_m)
    print(f"   → Created {len(hex_gdf)} hex cells")

    print("3) Aggregating amenities per hex...")
    amenities_proj = amenities.to_crs(epsg=3857)
    hex_gdf = aggregate_amenities(amenities_proj, hex_gdf)
    hex_gdf = compute_scores(
        hex_gdf,
        config.density_weight,
        config.diversity_weight,
    )

    print("4) Detecting cafe hotspots with DBSCAN...")
    hotspots = detect_hotspots(
        amenities_proj,
        amenity_type="cafe",
        eps=config.dbscan_eps,
        min_samples=config.dbscan_min_samples,
    )
    print(f"   → Found {len(hotspots)} hotspot clusters")

    print("5) Exporting GeoJSON files...")
    hex_gdf_wgs = hex_gdf.to_crs(epsg=4326)
    hex_path = config.output_folder / "cairo_hexgrid.geojson"
    hex_gdf_wgs.to_file(hex_path, driver="GeoJSON")

    hotspots_path = config.output_folder / "hotspots.geojson"
    if not hotspots.empty:
        hotspots_wgs = hotspots.to_crs(epsg=4326)
        hotspots_wgs.to_file(hotspots_path, driver="GeoJSON")

    print("6) Building interactive map...")
    amenities_wgs = amenities.to_crs(epsg=4326)
    hotspots_wgs = hotspots.to_crs(epsg=4326) if not hotspots.empty else hotspots
    area_wgs = area_gdf.to_crs(epsg=4326)

    m = create_map(hex_gdf_wgs, amenities_wgs, hotspots_wgs, area_wgs)
    map_path = config.output_folder / "cairo_hex_map.html"
    m.save(str(map_path))

    print("\nDone! Outputs:")
    print(f"  • Interactive map: {map_path}")
    print(f"  • Hex GeoJSON: {hex_path}")
    if hotspots_path.exists():
        print(f"  • Hotspots GeoJSON: {hotspots_path}")


if __name__ == "__main__":
    sys.exit(main())
