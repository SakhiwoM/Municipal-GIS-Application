import os
import sys
import io
import json
import folium
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QLabel, QMessageBox, 
                             QFrame, QSplitter, QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QHeaderView)
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

# Safe import from app/core/
try:
    from app.core.import_cadastre import process_csv_to_geojson
    from app.core.link_data import link_cadastre_to_valuation
    from app.core.map_layers import add_base_layers, build_geojson_click_handler, inject_qwebchannel_bridge
    from app.core.spatial_utils import get_preferred_plot_title
    from app.core.edit_gis import launch_external_gis
except ImportError:
    def process_csv_to_geojson(file_path):
        return {"type": "FeatureCollection", "features": []}
    def link_cadastre_to_valuation(s, c, join_column):
        return {"type": "FeatureCollection", "features": []}
    def add_base_layers(leaflet_map, google_maps_api_key=None):
        return leaflet_map
    def build_geojson_click_handler(bridge_object_name="mapBridge", method_name="handleFeatureClick"):
        return None
    def inject_qwebchannel_bridge(leaflet_map, bridge_object_name="mapBridge"):
        return leaflet_map
    def get_preferred_plot_title(properties, feature_id=None):
        return str(feature_id) if feature_id is not None else "Selected Plot"
    def launch_external_gis(file_path):
        return "Fallback"


class MapClickBridge(QObject):
    featureSelected = Signal(object)

    @Slot(str)
    def handleFeatureClick(self, feature_json):
        try:
            feature_data = json.loads(feature_json)
            if not isinstance(feature_data, dict):
                raise ValueError("Expected feature data to be an object.")
        except Exception:
            feature_data = {
                "id": None,
                "geometry": None,
                "properties": {},
                "raw": feature_json,
            }

        self.featureSelected.emit(feature_data)


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
        self.map_bridge = MapClickBridge(self)
        self.web_channel = QWebChannel(self.map_view.page())
        self.web_channel.registerObject("mapBridge", self.map_bridge)
        self.map_view.page().setWebChannel(self.web_channel)
        self.map_bridge.featureSelected.connect(self.update_attribute_panel)
        self.eswatini_center = [-26.52, 31.46]
        self.main_splitter.addWidget(self.map_view)

        # ----------------------------------------------------
        # PANEL 3 (RIGHT): ATTRIBUTE DETAILS SIDEBAR
        # ----------------------------------------------------
        self.attribute_panel = QFrame()
        self.attribute_panel.setFrameShape(QFrame.StyledPanel)
        self.attribute_panel.setStyleSheet("background-color: #ffffff;")
        self.attribute_panel.setMinimumWidth(280)

        attribute_layout = QVBoxLayout(self.attribute_panel)
        attribute_layout.setContentsMargins(10, 10, 10, 10)
        attribute_layout.setSpacing(8)

        self.attribute_title = QLabel("No plot selected")
        self.attribute_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        attribute_layout.addWidget(self.attribute_title)

        self.attribute_summary = QLabel("Click a plot on the map to view its cadastre attributes here.")
        self.attribute_summary.setWordWrap(True)
        self.attribute_summary.setStyleSheet("color: #34495e; font-size: 12px;")
        attribute_layout.addWidget(self.attribute_summary)

        self.attribute_table = QTableWidget(0, 2)
        self.attribute_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.attribute_table.verticalHeader().setVisible(False)
        self.attribute_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.attribute_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.attribute_table.setAlternatingRowColors(True)
        self.attribute_table.setWordWrap(True)
        self.attribute_table.horizontalHeader().setStretchLastSection(True)
        self.attribute_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        attribute_layout.addWidget(self.attribute_table)

        self.main_splitter.addWidget(self.attribute_panel)

        self.clear_attribute_panel()
        # Start with the attribute sidebar fully collapsed.
        self.main_splitter.setSizes([240, 860, 0])
        self.load_base_map(self.eswatini_center, starting_zoom=9)

    def load_base_map(self, center_coords, starting_zoom=9, geojson_overlay=None):
        """Generates a dynamic Leaflet map using folium and updates the view."""
        self.clear_attribute_panel()
        leaflet_map = folium.Map(
            location=center_coords,
            zoom_start=starting_zoom,
            tiles=None,
            control_scale=True
        )
        add_base_layers(leaflet_map, google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"))
        inject_qwebchannel_bridge(leaflet_map)

        if geojson_overlay and geojson_overlay.get("features"):
            renderable_features = [feature for feature in geojson_overlay["features"] if feature.get("geometry")]

            if renderable_features:
                renderable_geojson = dict(geojson_overlay)
                renderable_geojson["features"] = renderable_features

                geojson_layer = folium.GeoJson(
                    renderable_geojson,
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
                    popup=None,
                    on_each_feature=build_geojson_click_handler()
                )
                geojson_layer.add_to(leaflet_map)

        folium.LayerControl(collapsed=False).add_to(leaflet_map)

        map_buffer = io.BytesIO()
        leaflet_map.save(map_buffer, close_file=False)
        map_html_string = map_buffer.getvalue().decode()
        self.map_view.setHtml(map_html_string)

    def clear_attribute_panel(self):
        self.attribute_panel.hide()
        self.attribute_title.setText("No plot selected")
        self.attribute_summary.setText("Click a plot on the map to view its cadastre attributes here.")
        self.attribute_table.setRowCount(0)

    def update_attribute_panel(self, feature_data):
        self.attribute_panel.show()
        properties = feature_data.get("properties") or {}
        geometry = feature_data.get("geometry") or {}
        geometry_type = geometry.get("type") or "Unknown"
        feature_id = feature_data.get("id")

        selected_title = get_preferred_plot_title(properties, feature_id=feature_id)
        self.attribute_title.setText(selected_title)
        self.attribute_summary.setText(f"Geometry: {geometry_type}")

        rows = [
            ("Plot Title", self.format_attribute_value(selected_title)),
            ("Feature ID", self.format_attribute_value(feature_id)),
            ("Geometry Type", self.format_attribute_value(geometry_type)),
        ]
        for field_name, field_value in properties.items():
            rows.append((field_name, self.format_attribute_value(field_value)))

        self.attribute_table.setRowCount(len(rows))
        for row_index, (field_name, field_value) in enumerate(rows):
            field_item = QTableWidgetItem(str(field_name))
            value_item = QTableWidgetItem(str(field_value))
            field_item.setFlags(field_item.flags() & ~Qt.ItemIsEditable)
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            self.attribute_table.setItem(row_index, 0, field_item)
            self.attribute_table.setItem(row_index, 1, value_item)

        self.attribute_table.resizeRowsToContents()
        self.attribute_table.scrollToTop()
        self.main_splitter.setSizes([240, max(self.map_view.width(), 1), 300])

    @staticmethod
    def format_attribute_value(value):
        if value is None or value == "":
            return "-"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

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
                new_center = self.eswatini_center

                bbox = geojson_data.get("bbox")
                if bbox and len(bbox) == 4:
                    minx, miny, maxx, maxy = bbox
                    new_center = [(miny + maxy) / 2, (minx + maxx) / 2]
                else:
                    first_feat = next(
                        (feature for feature in geojson_data["features"] if feature.get("geometry")),
                        None
                    )
                    if first_feat:
                        geom_type = first_feat["geometry"]["type"]

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
                QMessageBox.warning(self, "Data Warning", "The file loaded successfully, but no renderable spatial features were found.")
                
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
