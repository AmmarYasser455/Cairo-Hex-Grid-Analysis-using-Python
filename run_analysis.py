#!/usr/bin/env python3
"""
Cairo Hex Grid Analysis - Main Entry Point

This script runs a complete hexagonal grid analysis of urban amenities
for Cairo, Egypt (or another specified location).

Usage:
    python run_analysis.py [--place "City, Country"] [--radius 400] [--output output/]

For more options:
    python run_analysis.py --help
"""

from hexanalysis.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
