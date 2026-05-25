# lanzarote-landcover

Classifying four decades of land cover change on Lanzarote (Canary Islands, Spain) using multi-decade Landsat satellite imagery, Google Earth Engine, and a Random Forest classifier.

## What this project does

Lanzarote has changed dramatically since the 1980s — coastal resort expansion, volcanic landscape dynamics, and shifts in agriculture driven by tourism. This project quantifies those changes pixel by pixel, using freely available satellite data and open-source tools.

The pipeline:
1. **Acquire** — query Landsat 5/7/8/9 imagery (1985–present) via Google Earth Engine
2. **Preprocess** — cloud masking, dry-season compositing, spectral index calculation
3. **Classify** — Random Forest trained on CORINE Land Cover labels (6 classes)
4. **Analyze** — transition matrices, area time series, change hotspot mapping
5. **Visualize** — interactive web map with time slider and analytics dashboard

## Land cover classes

| Class | Color |
|---|---|
| Urban / Built-up | `#E8443A` |
| Forest / Woodland | `#2D8C3C` |
| Water / Wetland | `#3B82F6` |
| Agriculture | `#F5C542` |
| Barren / Volcanic | `#4A4A4A` |
| Shrubland / Matorral | `#C4A86B` |

## Status

Currently in **Phase 1** — data exploration and GEE pipeline setup.

## Tech stack

Python · Google Earth Engine · scikit-learn · FastAPI · PostgreSQL/PostGIS · React · Leaflet

## Study area

Lanzarote + La Graciosa, Canary Islands, Spain — approximately 28.80°N–29.30°N, 13.30°W–13.90°W.

## License

MIT
