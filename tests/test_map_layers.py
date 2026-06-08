import unittest
from unittest.mock import Mock, patch

import folium

from app.core.map_layers import (
    add_base_layers,
    build_geojson_click_handler,
    build_google_satellite_layer,
    inject_qwebchannel_bridge,
)


class MapLayerTests(unittest.TestCase):
    def test_build_geojson_click_handler_targets_bridge(self):
        handler = build_geojson_click_handler()

        self.assertIn("mapBridge", handler.js_code)
        self.assertIn("handleFeatureClick", handler.js_code)
        self.assertIn("JSON.stringify(feature)", handler.js_code)

    def test_inject_qwebchannel_bridge_adds_bootstrap_script(self):
        leaflet_map = folium.Map(location=[-26.52, 31.46], tiles=None)
        inject_qwebchannel_bridge(leaflet_map)
        rendered_html = leaflet_map.get_root().render()

        self.assertIn("qwebchannel.js", rendered_html)
        self.assertIn("initializeQtWebChannel", rendered_html)

    @patch("app.core.map_layers.requests.post")
    def test_build_google_satellite_layer_uses_session_token(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"session": "test-session-token"}
        mock_post.return_value = mock_response

        layer = build_google_satellite_layer("test-api-key")

        self.assertIsNotNone(layer)
        self.assertIn("tile.googleapis.com/v1/2dtiles", layer.tiles)
        self.assertIn("session=test-session-token", layer.tiles)
        self.assertIn("key=test-api-key", layer.tiles)

    @patch("app.core.map_layers.requests.post")
    def test_add_base_layers_includes_google_when_configured(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"session": "test-session-token"}
        mock_post.return_value = mock_response

        leaflet_map = folium.Map(location=[-26.52, 31.46], tiles=None)
        add_base_layers(leaflet_map, google_maps_api_key="test-api-key")
        folium.LayerControl(collapsed=False).add_to(leaflet_map)
        rendered_html = leaflet_map.get_root().render()

        tile_layer_count = sum(
            1 for child in leaflet_map._children.values()
            if isinstance(child, folium.raster_layers.TileLayer)
        )

        self.assertEqual(tile_layer_count, 3)
        self.assertIn("tile.googleapis.com/v1/2dtiles", rendered_html)


if __name__ == "__main__":
    unittest.main()
