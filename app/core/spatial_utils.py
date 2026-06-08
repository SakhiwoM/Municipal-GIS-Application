import json


def normalize_column_names(geodataframe):
    """Return a copy with consistently trimmed, lower-case column names."""
    normalized = geodataframe.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    return normalized


def _normalize_property_key(property_key):
    return str(property_key).strip().lower().replace(" ", "").replace("_", "")


def _has_renderable_geometry(geometry):
    return geometry is not None and not getattr(geometry, "is_empty", True)


def drop_empty_geometries(geodataframe):
    """Return only rows with non-empty, non-null geometries."""
    if geodataframe.empty:
        return geodataframe.copy()

    valid_geometry_mask = geodataframe.geometry.map(_has_renderable_geometry)
    return geodataframe.loc[valid_geometry_mask].copy()


def geodataframe_to_feature_collection(geodataframe):
    """Serialize a cleaned GeoDataFrame into a GeoJSON FeatureCollection."""
    cleaned_geodataframe = drop_empty_geometries(geodataframe)
    feature_collection = json.loads(cleaned_geodataframe.to_json())

    if not cleaned_geodataframe.empty:
        minx, miny, maxx, maxy = map(float, cleaned_geodataframe.total_bounds)
        feature_collection["bbox"] = [minx, miny, maxx, maxy]

    return feature_collection


def get_preferred_plot_title(properties, feature_id=None):
    """Pick the most useful human-readable title for a clicked plot."""
    if not properties:
        properties = {}

    normalized_properties = {
        _normalize_property_key(property_key): property_value
        for property_key, property_value in properties.items()
    }

    preferred_keys = (
        "text value",
        "text_value",
        "textvalue",
        "refname",
        "ref_name",
        "ref name",
        "name",
        "title",
        "erf_id",
    )

    for preferred_key in preferred_keys:
        normalized_key = _normalize_property_key(preferred_key)
        value = normalized_properties.get(normalized_key)
        if value not in (None, ""):
            return str(value)

    if feature_id not in (None, ""):
        return str(feature_id)

    return "Selected Plot"
