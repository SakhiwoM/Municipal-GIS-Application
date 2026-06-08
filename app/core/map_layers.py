import requests
import folium
from branca.element import Element
from folium.features import GeoJsonPopup
from folium.utilities import JsCode


def build_geojson_popup(property_fields):
    if not property_fields:
        return None

    aliases = [field.upper() for field in property_fields]
    return GeoJsonPopup(
        fields=property_fields,
        aliases=aliases,
        labels=True,
        localize=True,
        style="""
            background-color: #ffffff;
            border: 1px solid #2c3e50;
            border-radius: 4px;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
            font-family: sans-serif;
            font-size: 11px;
            padding: 8px;
            color: #2c3e50;
        """,
    )


def build_geojson_click_handler(bridge_object_name="mapBridge", method_name="handleFeatureClick"):
    return JsCode(
        f"""
        function(feature, layer) {{
            layer.on({{
                click: function() {{
                    if (window.{bridge_object_name} && window.{bridge_object_name}.{method_name}) {{
                        window.{bridge_object_name}.{method_name}(JSON.stringify(feature));
                    }}
                }}
            }});
        }}
        """
    )


def inject_qwebchannel_bridge(leaflet_map, bridge_object_name="mapBridge"):
    root = leaflet_map.get_root()
    root.header.add_child(Element('<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'))
    root.script.add_child(
        Element(
            f"""
            function initializeQtWebChannel() {{
                if (typeof qt === 'undefined' || !qt.webChannelTransport || window.{bridge_object_name}) {{
                    return;
                }}

                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    window.{bridge_object_name} = channel.objects.{bridge_object_name};
                }});
            }}

            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', initializeQtWebChannel);
            }} else {{
                initializeQtWebChannel();
            }}
            """
        )
    )
    return leaflet_map


def build_google_satellite_layer(api_key, region="US", language="en-US", show=False):
    if not api_key:
        return None

    try:
        response = requests.post(
            "https://tile.googleapis.com/v1/createSession",
            params={"key": api_key},
            json={"mapType": "satellite", "language": language, "region": region},
            timeout=10,
        )
        response.raise_for_status()

        session_token = response.json().get("session")
        if not session_token:
            return None
    except Exception:
        return None

    tiles_url = (
        "https://tile.googleapis.com/v1/2dtiles/{z}/{x}/{y}"
        f"?session={session_token}&key={api_key}"
    )

    return folium.TileLayer(
        tiles=tiles_url,
        attr="Google Maps Platform",
        name="Google Satellite",
        overlay=False,
        control=True,
        show=show,
        max_zoom=22,
    )


def add_base_layers(leaflet_map, google_maps_api_key=None):
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap",
        overlay=False,
        control=True,
        show=True,
    ).add_to(leaflet_map)

    google_layer = build_google_satellite_layer(google_maps_api_key)
    if google_layer:
        google_layer.add_to(leaflet_map)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        name="Satellite Imagery",
        overlay=False,
        control=True,
        show=False,
        max_zoom=19,
    ).add_to(leaflet_map)

    return leaflet_map
