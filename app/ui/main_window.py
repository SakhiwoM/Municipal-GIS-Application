import os
import sys
import json
import io
import folium
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QLabel, QMessageBox, 
                             QFrame, QSplitter)
from PySide6.QtCore import Qt
from PySide6.QtWebEngineWidgets import QWebEngineView

# Safe import from app/core/
try:
    from app.core.import_cadastre import process_csv_to_geojson
    from app.core.link_data import link_cadastre_to_valuation
    from app.core.edit_gis import launch_external_gis
except ImportError:
    def process_csv_to_geojson(file_path):
        return {"type": "FeatureCollection", "features": []}
    def link_cadastre_to_valuation(s, c, join_column):
        return {"type": "FeatureCollection", "features": []}
    def launch_external_gis(file_path):
        return "Fallback"


class CollapsibleMenu(QWidget):
    """A custom widget to create an expandable left-aligned menu container."""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        
        self.toggle_btn = QPushButton(f"▼ {title}")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2c3e50;
                color: white;
                font-weight: bold;
                text-align: left;
                padding: 10px;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #34495e; }
        """)
        self.toggle_btn.clicked.connect(self.toggle_menu)
        self.layout.addWidget(self.toggle_btn)
        
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 5, 0, 5)
        self.content_layout.setSpacing(6)
        self.layout.addWidget(self.content_frame)
        self.is_expanded = True

    def toggle_menu(self):
        if self.is_expanded:
            self.content_frame.hide()
            self.toggle_btn.setText(f"► {self.toggle_btn.text()[2:]}")
        else:
            self.content_frame.show()
            self.toggle_btn.setText(f"▼ {self.toggle_btn.text()[2:]}")
        self.is_expanded = not self.is_expanded

    def add_button(self, text, callback, color="#f0f0f0", hover_color="#e0e0e0", text_color="#000000"):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                font-weight: normal;
                padding: 10px;
                border: 1px solid #bcbcbc;
                border-radius: 4px;
                text-align: left;
                padding-left: 15px;
            }}
            QPushButton:hover {{ background-color: {hover_color}; }}
        """)
        btn.clicked.connect(callback)
        self.content_layout.addWidget(btn)
        return btn


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Municipal GIS Application - Eswatini Workspace")
        self.resize(1100, 768)

        # Main horizontal splitter layout to manage column panels dynamically
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_splitter)

        # ----------------------------------------------------
        # PANEL 1 (FAR LEFT): EXPANDABLE CONTROL SIDEBAR
        # ----------------------------------------------------
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)
        
        self.sidebar_title = QLabel("GIS CONTROL PANEL")
        self.sidebar_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-bottom: 5px;")
        sidebar_layout.addWidget(self.sidebar_title)

        self.menu_operations = CollapsibleMenu("Data & Core Operations")
        self.menu_operations.add_button("Import Cadastre", self.trigger_cadastre_import, "#f0f0f0", "#e0e0e0")
        self.menu_operations.add_button("Import Valuation Roll", self.placeholder_action, "#f0f0f0", "#e0e0e0")
        self.menu_operations.add_button("Link Data", self.trigger_data_linking, "#f0f0f0", "#e0e0e0")
        self.menu_operations.add_button("Edit in GIS Software", self.trigger_external_gis, "#f0f0f0", "#e0e0e0")
        
        sidebar_layout.addWidget(self.menu_operations)
        sidebar_layout.addStretch()
        self.main_splitter.addWidget(sidebar)
        
        # ----------------------------------------------------
        # PANEL 2 (CENTER/MAIN): LIVE LEAFLET MAP VIEWPORT
        # ----------------------------------------------------
        self.map_view = QWebEngineView()
        self.eswatini_center = [-26.52, 31.46]
        self.main_splitter.addWidget(self.map_view)

        # Set final default splitter sizes (Sidebar takes 240px, Map expands to fill the rest)
        self.main_splitter.setSizes([240, 860])
        
        self.load_base_map(self.eswatini_center, starting_zoom=9)

    def load_base_map(self, center_coords, starting_zoom=9, geojson_overlay=None):
        """Generates a dynamic Leaflet map using folium and updates the view."""
        leaflet_map = folium.Map(
            location=center_coords,
            zoom_start=starting_zoom,
            tiles="OpenStreetMap",
            control_scale=True
        )

        if geojson_overlay and geojson_overlay.get("features"):
            # Dynamically extract all unique feature property attributes key labels from dataset 
            # to map them comprehensively inside the popup tooltip matrix structure
            sample_feature = geojson_overlay["features"][0]
            property_fields = list(sample_feature.get("properties", {}).keys())

            if property_fields:
                # Setup custom styled table HTML formatting matrix for clear rendering on hover
                aliases = [f"<b>{field.upper()}:</b>" for field in property_fields]
                map_tooltip = folium.GeoJsonTooltip(
                    fields=property_fields,
                    aliases=aliases,
                    localize=True,
                    sticky=True,
                    style="""
                        background-color: #ffffff;
                        border: 1px solid #2c3e50;
                        border-radius: 4px;
                        box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
                        font-family: sans-serif;
                        font-size: 11px;
                        padding: 8px;
                        color: #2c3e50;
                    """
                )
            else:
                map_tooltip = None

            geojson_layer = folium.GeoJson(
                geojson_overlay,
                name="Cadastre Layer",
                style_function=lambda x: {
                    'fillColor': '#3498db',
                    'color': '#2980b9',
                    'weight': 1.5,
                    'fillOpacity': 0.4
                },
                highlight_function=lambda x: {
                    'fillColor': '#3498db',
                    'color': '#e74c3c',
                    'weight': 3.5,
                    'fillOpacity': 0.6
                },
                tooltip=map_tooltip
            )
            geojson_layer.add_to(leaflet_map)
            folium.LayerControl().add_to(leaflet_map)

        map_buffer = io.BytesIO()
        leaflet_map.save(map_buffer, close_file=False)
        map_html_string = map_buffer.getvalue().decode()
        self.map_view.setHtml(map_html_string)

    def trigger_cadastre_import(self):
        """Processes a shapefile and dynamically re-renders it on the live map view."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Cadastre Vector Dataset", 
            "", 
            "Spatial Vector Files (*.shp *.zip *.geojson *.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            geojson_data = process_csv_to_geojson(file_path)
            
            if geojson_data and geojson_data.get("features"):
                first_feat = geojson_data["features"][0]
                geom_type = first_feat["geometry"]["type"]
                new_center = self.eswatini_center
                
                if geom_type == "Point":
                    coords = first_feat["geometry"]["coordinates"]
                    new_center = [coords[1], coords[0]]
                elif geom_type in ["Polygon", "MultiPolygon"]:
                    if geom_type == "Polygon":
                        first_pt = first_feat["geometry"]["coordinates"][0][0]
                    else:
                        first_pt = first_feat["geometry"]["coordinates"][0][0][0]
                    new_center = [first_pt[1], first_pt[0]]

                self.load_base_map(center_coords=new_center, starting_zoom=14, geojson_overlay=geojson_data)
                
                total_records = len(geojson_data["features"])
                QMessageBox.information(
                    self, 
                    "Import & Render Complete", 
                    f"Successfully mapped {total_records} features onto the interactive view!"
                )
            else:
                QMessageBox.warning(self, "Data Warning", "The file was parsed but contains empty spatial vectors.")
                
        except Exception as e:
            QMessageBox.critical(self, "Processing Error", f"Failed to display layers on Leaflet engine:\n{str(e)}")

    def trigger_data_linking(self):
        shapefile_path, _ = QFileDialog.getOpenFileName(self, "Select Cadastre Dataset", "", "Spatial Files (*.shp *.zip *.geojson)")
        if not shapefile_path: return
        csv_path, _ = QFileDialog.getOpenFileName(self, "Select Valuation Ledger (.csv)", "", "CSV Files (*.csv)")
        if not csv_path: return

        try:
            linked_geojson = link_cadastre_to_valuation(shapefile_path, csv_path, join_column="erf_id")
            if linked_geojson and linked_geojson.get("features"):
                self.load_base_map(center_coords=self.eswatini_center, starting_zoom=10, geojson_overlay=linked_geojson)
                QMessageBox.information(self, "Success", "Attributes merged and drawn on Leaflet view!")
        except Exception as e:
            QMessageBox.critical(self, "Linking Error", f"Failed link matrix:\n{str(e)}")

    def trigger_external_gis(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select GIS Layer", "", "Spatial Files (*.shp *.zip *.geojson)")
        if not file_path: return
        try:
            software_name = launch_external_gis(file_path)
            QMessageBox.information(self, "External GIS", f"Handing off file to {software_name}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def placeholder_action(self):
        QMessageBox.information(self, "System Update", "Module active.")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())