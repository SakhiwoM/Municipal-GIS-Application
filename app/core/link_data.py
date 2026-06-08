import pandas as pd
import geopandas as gpd

from .spatial_utils import geodataframe_to_feature_collection, normalize_column_names

def link_cadastre_to_valuation(shapefile_path, valuation_csv_path, join_column="erf_id"):
    """
    Performs a spatial-tabular attributes join. It links your spatial 
    cadastre boundaries to the municipal valuation roll sheet using a shared ID.
    """
    try:
        # 1. Read your spatial cadastre layer (Shapefile)
        gdf = gpd.read_file(shapefile_path)
        gdf = normalize_column_names(gdf)

        # 2. Read your tabular financial records sheet (CSV Valuation Roll)
        df = pd.read_csv(valuation_csv_path)
        df.columns = [str(column).strip().lower() for column in df.columns]

        # Normalize the join column name to lower-case to prevent matching issues
        join_column = join_column.strip().lower()

        if join_column not in gdf.columns or join_column not in df.columns:
            raise ValueError(f"Shared index column '{join_column}' was not found in one of your datasets.")

        # 3. Execute an Attribute Join (combines property lines with accounting data)
        # Keeps all map features, attaching financial records where they match
        merged_gdf = gdf.merge(df, on=join_column, how="left")

        # 4. Transform coordinates to standard GPS (WGS84) for web visualization mapping
        if merged_gdf.crs and merged_gdf.crs.to_string() != "EPSG:4326":
            merged_gdf = merged_gdf.to_crs(epsg=4326)

        # 5. Convert back into a standard Python dictionary GeoJSON payload
        return geodataframe_to_feature_collection(merged_gdf)

    except Exception as e:
        raise RuntimeError(f"Database Join Failure: {str(e)}")
