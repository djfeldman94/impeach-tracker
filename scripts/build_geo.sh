#!/usr/bin/env bash
#
# Download Census 2024 Cartographic Boundary files and convert to TopoJSON.
# Requires: mapshaper (npm install -D mapshaper)
#
# Usage: bash scripts/build_geo.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="/tmp/geo-build-$$"
OUTPUT_DIR="$PROJECT_DIR/public/geo"

DISTRICTS_URL="https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_cd119_500k.zip"
STATES_URL="https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip"

SIMPLIFY_PCT="15%"
QUANTIZATION="1e5"

cleanup() {
  rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

echo "==> Creating build directory: $BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "==> Downloading congressional district boundaries (119th Congress, 1:500k)..."
curl -sL "$DISTRICTS_URL" -o "$BUILD_DIR/districts.zip"

echo "==> Downloading state boundaries (1:500k)..."
curl -sL "$STATES_URL" -o "$BUILD_DIR/states.zip"

echo "==> Extracting..."
unzip -q -o "$BUILD_DIR/districts.zip" -d "$BUILD_DIR/districts/"
unzip -q -o "$BUILD_DIR/states.zip" -d "$BUILD_DIR/states/"

echo "==> Converting districts to TopoJSON (simplify: $SIMPLIFY_PCT, quantize: $QUANTIZATION)..."
npx mapshaper "$BUILD_DIR/districts/cb_2024_us_cd119_500k.shp" \
  -filter-fields GEOID,STATEFP,CD119FP,NAMELSAD \
  -rename-fields GEOID=GEOID,STATEFP=STATEFP,CD=CD119FP,NAME=NAMELSAD \
  -simplify dp "$SIMPLIFY_PCT" \
  -o format=topojson quantization="$QUANTIZATION" "$BUILD_DIR/us-congress-districts.topo.json"

echo "==> Converting states to TopoJSON (simplify: $SIMPLIFY_PCT, quantize: $QUANTIZATION)..."
npx mapshaper "$BUILD_DIR/states/cb_2024_us_state_500k.shp" \
  -filter-fields GEOID,STATEFP,STUSPS,NAME \
  -simplify dp "$SIMPLIFY_PCT" \
  -o format=topojson quantization="$QUANTIZATION" "$BUILD_DIR/us-states.topo.json"

echo "==> Copying to $OUTPUT_DIR..."
mkdir -p "$OUTPUT_DIR"
cp "$BUILD_DIR/us-congress-districts.topo.json" "$OUTPUT_DIR/"
cp "$BUILD_DIR/us-states.topo.json" "$OUTPUT_DIR/"

echo ""
echo "==> Done! File sizes:"
ls -lh "$OUTPUT_DIR/us-congress-districts.topo.json" "$OUTPUT_DIR/us-states.topo.json"
