import geopandas as gpd

from .spatial_utils import geodataframe_to_feature_collection, normalize_column_names


def process_csv_to_geojson(file_path):
    """
    Reads a vector dataset and converts it into a GeoJSON FeatureCollection.
    Empty or missing geometries are removed before serialization.
    """
    try:
        gdf = gpd.read_file(file_path)
        gdf = normalize_column_names(gdf)

        if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)

        return geodataframe_to_feature_collection(gdf)

    except Exception as e:
        raise RuntimeError(f"Error reading shapefile vector array: {str(e)}")
