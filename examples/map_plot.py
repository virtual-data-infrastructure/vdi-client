# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025 VDI contributors
"""
Example script for the VDI client.

Reads a GeoJSON file and produces a PNG map plot using geopandas and matplotlib.
Intended to be run via the VDI client wrapper (``vdi run python examples/map_plot.py``).
"""

# Standard library imports
import argparse
import os

# Third-party imports
import geopandas as gpd
import matplotlib.pyplot as plt

# create the parser
parser = argparse.ArgumentParser(description="Script to plot GeoJSON data")

# add arguments
parser.add_argument("filename", type=str, help="The name of the GeoJSON file to process.")
parser.add_argument("--out", type=str, default=".", help="Directory to create output files in (default: .).")

# parse the arguments
args = parser.parse_args()

# read the GeoJSON file
any_map = gpd.read_file(args.filename)

# create a plot
fig, ax = plt.subplots(figsize=(10, 10))

# plot the map
any_map.plot(ax=ax, color="white", edgecolor="black")

# customize the plot
plt.title('A map for "' + args.filename + '"')
plt.xlabel("Longitude")
plt.ylabel("Latitude")

# make sure the output directory exists
os.makedirs(args.out, exist_ok=True)

# save the plot as a PNG file
png_path = args.out + "/" + os.path.basename(args.filename) + "_map.png"
plt.savefig(png_path, dpi=300)
print(f"created PNG-file '{png_path}'")

# optionally, show the plot
# plt.show()
