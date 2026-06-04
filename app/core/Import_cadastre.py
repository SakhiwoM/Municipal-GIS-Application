import json
import geopandas as gpd

def process_csv_to_geojson(file_path):
    """
    Parses a native GIS Shapefile (.shp) and extracts its vector structures 
    into a standardized GeoJSON dictionary object payload.
    """
    try:
        # 1. Read the vector file data natively using GeoPandas
        gdf = gpd.read_file(file_path)

        # 2. Normalize attribute column strings to lower-case for downstream consistency
        gdf.columns = gdf.columns.str.strip().str.lower()

        # 3. Shapefiles can use localized projecting zones (like UTM or Lo).
        # We transform it automatically to standard GPS coordinates (WGS84) for web platforms.
        if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)
        
        # 4. Serialize spatial structures into a functional Python data dictionary
        geojson_data = json.loads(gdf.to_json())
        return geojson_data
        
    except Exception as e:
        # Passes the error trace backward to main_window.py to spawn an error dialogue box
        raise RuntimeError(f"Error reading shapefile vector array: {str(e)}")