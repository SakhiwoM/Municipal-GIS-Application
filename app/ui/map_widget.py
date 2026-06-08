from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView


class MapWidget(QWidget):
    """A widget that displays a Leaflet map in a QWebEngineView."""
    
    def __init__(self, parent=None, center_lat=-26.5225, center_lon=31.4659, zoom_start=8):
        super().__init__(parent)
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        
        # Create QWebEngineView for displaying the map
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)
        
        # Generate and display the map
        self.create_map(center_lat, center_lon, zoom_start)
    
    def create_map(self, center_lat=-26.5225, center_lon=31.4659, zoom_start=8):
        """Create a Leaflet map centered on Eswatini and display it."""
        
        # Create HTML with Leaflet from CDN
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Eswatini GIS Map</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.css" />
            <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.js"></script>
            <style>
                * {{ margin: 0; padding: 0; }}
                body {{ height: 100vh; width: 100%; }}
                #map {{ height: 100%; width: 100%; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                // Initialize the map
                var map = L.map('map').setView([{float(center_lat)}, {float(center_lon)}], {int(zoom_start)});
                
                // Add OpenStreetMap tiles
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap contributors',
                    maxZoom: 22
                }}).addTo(map);
            </script>
        </body>
        </html>
        """
        
        # Load HTML directly into the web view
        self.web_view.setHtml(html)
    
    def update_map_center(self, lat, lon, zoom_start=8):
        """Update the map center to a new location."""
        self.create_map(lat, lon, zoom_start)
    
    def add_marker(self, lat, lon, popup_text="Marker", tooltip_text=""):
        """Add a marker to the map (requires recreating map currently)."""
        pass  # TODO: Implement dynamic marker addition




