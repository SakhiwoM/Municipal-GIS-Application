import pandas as pd
import geopandas as gpd
import os
from .spatial_utils import geodataframe_to_feature_collection, normalize_column_names


def _clean_link_part(value):
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def _build_valuation_link_key(type_val, no_val, ptn_val):
    type_text = _clean_link_part(type_val).upper()
    no_text = _clean_link_part(no_val)
    ptn_text = _clean_link_part(ptn_val)
    ptn_upper = ptn_text.upper()

    if not no_text or no_text.upper() in ("NAN", "NONE"):
        return None

    if type_text in ("LOT", "L", "ERF", "E"):
        return no_text

    if ptn_upper in ("", "NAN", "NONE", "REM"):
        return f"R/{no_text}"

    if ptn_upper.startswith("REM"):
        suffix = ptn_upper[3:].strip()
        return f"R/{suffix}/{no_text}" if suffix else f"R/{no_text}"

    return f"{ptn_text}/{no_text}"


def link_cadastre_to_valuation(shapefile_path, valuation_csv_path, join_column="erf_id"):
    """
    Performs a safe spatial-tabular attributes join by auto-resolving 
    column name differences and matching conflicting data types.
    """
    file_ext = os.path.splitext(valuation_csv_path)[1].lower()
    
    try:
        # 1. Read spatial layer
        gdf = gpd.read_file(shapefile_path)
        gdf = normalize_column_names(gdf)

        # 2. Read tabular dataset using row index header scan
        if file_ext in ['.xlsx', '.xls']:
            df_raw = pd.read_excel(valuation_csv_path, header=None)
        else:
            df_raw = pd.read_csv(valuation_csv_path, header=None, encoding='utf-8', errors='replace')
        
        header_row_idx = 0
        for idx, row in df_raw.iterrows():
            row_strs = [str(val).strip().lower() for val in row.values if pd.notna(val)]
            if "property owner's name" in row_strs or ('type' in row_strs and 'no' in row_strs):
                header_row_idx = idx
                break

        if file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(valuation_csv_path, skiprows=header_row_idx)
        else:
            df = pd.read_csv(valuation_csv_path, skiprows=header_row_idx, encoding='utf-8', errors='replace')

        df.columns = [str(column).strip() for column in df.columns]
        target_join = join_column.strip().lower()

        # 3. Build the same cadastre key on both sides.
        # The Malkerns cadastre stores the real parcel reference in "text"
        # while the valuation roll stores Type / No / Ptn parts.
        cadastre_key_col = None
        for col in ["text", target_join, "erf_id", "plot_no", "parcel_no", "plot", "id", "no"]:
            if col in gdf.columns:
                cadastre_key_col = col
                break

        type_col = no_col = ptn_col = None
        for col in df.columns:
            normalized = str(col).strip().lower()
            if normalized == "type":
                type_col = col
            elif normalized == "no":
                no_col = col
            elif normalized == "ptn":
                ptn_col = col

        if cadastre_key_col is None:
            raise ValueError(f"Could not locate a cadastre parcel key. Cadastre fields: {list(gdf.columns)[:8]}...")

        gdf["__link_key"] = gdf[cadastre_key_col].map(_clean_link_part)

        if type_col is not None and no_col is not None:
            df["__link_key"] = df.apply(
                lambda row: _build_valuation_link_key(
                    row.get(type_col, ""),
                    row.get(no_col, ""),
                    row.get(ptn_col, "") if ptn_col else "",
                ),
                axis=1,
            )
        else:
            df_join_col = None
            for col in df.columns:
                if str(col).lower().strip() in [target_join, "erf_id", "plot_no", "parcel_no", "plot", "id", "no"]:
                    df_join_col = col
                    break
            if df_join_col is None:
                raise ValueError(
                    f"Could not locate a valuation parcel key.\n"
                    f"Valuation fields: {list(df.columns)[:8]}..."
                )
            df["__link_key"] = df[df_join_col].map(_clean_link_part)

        df = df[df["__link_key"].notna() & (df["__link_key"].astype(str).str.strip() != "")]
        df = df.drop_duplicates(subset="__link_key", keep="first")

        # 4. Execute Attribute Join
        merged_gdf = gdf.merge(df, on="__link_key", how="left").drop(columns=["__link_key"], errors="ignore")

        if merged_gdf.crs and merged_gdf.crs.to_string() != "EPSG:4326":
            merged_gdf = merged_gdf.to_crs(epsg=4326)

        return geodataframe_to_feature_collection(merged_gdf)

    except Exception as e:
        raise RuntimeError(f"Database Join Failure: {str(e)}")
