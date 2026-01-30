"""Configuration constants for hex grid analysis."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """
    Configuration for hex grid analysis.

    Attributes:
        place_name: Name of the place to analyze (geocoded via OSMnx).
        hex_radius_m: Radius of hexagons in meters.
        output_folder: Path to save output files.
        amenity_types: List of amenity types to include in analysis.
        dbscan_eps: DBSCAN epsilon (max distance in meters).
        dbscan_min_samples: DBSCAN minimum cluster size.
        density_weight: Weight for density in score calculation.
        diversity_weight: Weight for diversity in score calculation.
    """

    place_name: str = "Cairo, Egypt"
    hex_radius_m: float = 400.0
    output_folder: Path = field(default_factory=lambda: Path("data"))

    amenity_types: list[str] = field(
        default_factory=lambda: [
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
    )

    # DBSCAN parameters for hotspot detection
    dbscan_eps: float = 200.0  # meters
    dbscan_min_samples: int = 3

    # Score weights (must sum to 1.0)
    density_weight: float = 0.65
    diversity_weight: float = 0.35

    def __post_init__(self) -> None:
        """Ensure output folder exists."""
        self.output_folder = Path(self.output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
