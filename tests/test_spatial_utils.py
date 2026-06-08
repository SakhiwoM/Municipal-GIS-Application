import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon

from app.core.import_cadastre import process_csv_to_geojson
from app.core.spatial_utils import drop_empty_geometries, get_preferred_plot_title


class SpatialUtilsTests(unittest.TestCase):
    def test_drop_empty_geometries_removes_null_and_empty_rows(self):
        geodataframe = gpd.GeoDataFrame(
            {"id": [1, 2, 3]},
            geometry=[Point(31.46, -26.52), None, Polygon()],
            crs="EPSG:4326",
        )

        cleaned_geodataframe = drop_empty_geometries(geodataframe)

        self.assertEqual(len(cleaned_geodataframe), 1)
        self.assertEqual(cleaned_geodataframe.iloc[0]["id"], 1)
        self.assertFalse(cleaned_geodataframe.geometry.isna().any())
        self.assertFalse(cleaned_geodataframe.geometry.is_empty.any())

    def test_process_csv_to_geojson_skips_empty_geometries(self):
        geodataframe = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[Point(31.46, -26.52), None],
            crs="EPSG:4326",
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            geojson_path = Path(temporary_directory) / "cadastre.geojson"
            geojson_path.write_text(geodataframe.to_json(), encoding="utf-8")

            geojson_data = process_csv_to_geojson(str(geojson_path))

        self.assertEqual(len(geojson_data["features"]), 1)
        self.assertEqual(geojson_data["features"][0]["geometry"]["type"], "Point")
        self.assertEqual(geojson_data["bbox"], [31.46, -26.52, 31.46, -26.52])

    def test_get_preferred_plot_title_prefers_text_value_then_refname(self):
        properties = {"text value": "Plot 42", "refname": "ERF-12"}

        self.assertEqual(get_preferred_plot_title(properties), "Plot 42")

        properties = {"refname": "ERF-12"}
        self.assertEqual(get_preferred_plot_title(properties), "ERF-12")

        self.assertEqual(get_preferred_plot_title({}, feature_id="7"), "7")


if __name__ == "__main__":
    unittest.main()
