"""
Map Tile Generator
===================

Converts classified GeoTIFFs into XYZ map tiles (PNG) for the web frontend.

Uses rio-tiler for on-the-fly tiling, or pre-renders tiles at zoom levels
8–14 for the demo region (Lanzarote) to ensure fast frontend load times.

Colour mapping follows config.CLASS_COLORS.
"""

# TODO (Phase 4): Implement tile generation with rio-tiler


def generate_tile(raster_path: str, z: int, x: int, y: int) -> bytes:
    """
    Return a PNG tile for the given TMS coordinates.
    """
    raise NotImplementedError("Phase 4")


def prerender_tiles(raster_path: str, output_dir: str,
                    min_zoom: int = 8, max_zoom: int = 14) -> None:
    """
    Pre-render all tiles at the specified zoom range.
    Tiles are saved to output_dir/{z}/{x}/{y}.png.
    """
    raise NotImplementedError("Phase 4")
