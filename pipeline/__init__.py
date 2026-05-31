"""
Lanzarote Land Cover — Processing Pipeline
==========================================

Modules
-------
config          Central constants, class definitions, band mappings
acquire         Data acquisition via Google Earth Engine
preprocess      Cloud masking, compositing, reprojection, clipping
indices         Spectral index calculations (NDVI, NDWI, NDBI, SAVI, BSI, EVI)
classify        Random Forest training, prediction, evaluation
change_detection Transition matrices, area time series, change hotspot mapping
postprocess     Spatial filtering, smoothing, artefact removal
tile_generator  Convert classified rasters to XYZ map tiles
utils           Shared helpers (I/O, logging, CRS utilities)
"""
