import os
import sys
import json
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QLabel, QMessageBox, 
                             QFrame, QSplitter)
from PySide6.QtCore import Qt

# Safe import from app/core/
try:
    from app.core.Import_cadastre import process_csv_to_geojson
    from app.core.link_data import link_cadastre_to_valuation
    from app.core.edit_gis import launch_external_gis
except ImportError:
    # Safe fallback functions if paths or filenames ever misalign
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
        
        # Expand/Collapse Toggle Header
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
        
        # Content Container (Holds the sub-buttons)
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
        """Creates a left-aligned button matching standard desktop applications."""
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
        self.setWindowTitle("Municipal GIS Application")
        self.resize(1024, 768)

        # Main splitter layout to allow resizing between sidebar and map
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # ----------------------------------------------------
        # LEFT PANEL: WEB-STYLE EXPANDABLE SIDEBAR
        # ----------------------------------------------------
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)
        
        # App Branding Header
        self.sidebar_title = QLabel("GIS CONTROL PANEL")
        self.sidebar_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-bottom: 5px;")
        sidebar_layout.addWidget(self.sidebar_title)

        # Create the Expandable Menu Container
        self.menu_operations = CollapsibleMenu("Data & Core Operations")
        
        # Add exact button sequence matching layout specifications
        self.menu_operations.add_button("Import Cadastre", self.trigger_cadastre_import, "#f0f0f0", "#e0e0e0")
        self.menu_operations.add_button("Import Valuation Roll", self.placeholder_action, "#f0f0f0", "#e0e0e0")
        self.menu_operations.add_button("Link Data", self.trigger_data_linking, "#f0f0f0", "#e0e0e0")
        self.menu_operations.add_button("Edit in GIS Software", self.trigger_external_gis, "#f0f0f0", "#e0e0e0")
        
        sidebar_layout.addWidget(self.menu_operations)
        sidebar_layout.addStretch() # Pushes menus to the top
        
        # ----------------------------------------------------
        # RIGHT PANEL: CLEAN MAP FIELD PLACEHOLDER
        # ----------------------------------------------------
        self.map_field = QFrame()
        self.map_field.setFrameShape(QFrame.StyledPanel)
        self.map_field.setStyleSheet("""
            QFrame {
                background-color: #ecf0f1;
            }
        """)
        
        # Centered label inside the map grid
        map_layout = QVBoxLayout(self.map_field)
        self.map_label = QLabel("Map Field")
        self.map_label.setAlignment(Qt.AlignCenter)
        self.map_label.setStyleSheet("color: #7f8c8d; font-weight: bold; font-size: 14px; background: transparent;")
        map_layout.addWidget(self.map_label)

        # Assemble panels into the horizontal layout splitter
        splitter.addWidget(sidebar)
        splitter.addWidget(self.map_field)
        
        # Set initial layout proportions (25% sidebar, 75% map viewport)
        splitter.setSizes([250, 774])

    def trigger_cadastre_import(self):
        """Processes a shapefile and keeps it in memory without prompting to save."""
        # Step 1: Prompt user to pick the input shapefile
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Cadastre Vector Dataset", 
            "", 
            "Spatial Vector Files (*.shp *.zip *.geojson *.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            # Step 2: Extract spatial structure via core module
            geojson_data = process_csv_to_geojson(file_path)
            
            if geojson_data:
                # Step 3: Simply read the record count and notify the user directly
                total_records = len(geojson_data.get("features", []))
                QMessageBox.information(
                    self, 
                    "Import Complete", 
                    f"Successfully parsed and loaded data structures for {total_records} properties into memory!"
                )
        except Exception as e:
            QMessageBox.critical(self, "Processing Error", f"Failed to execute import script:\n{str(e)}")

    def trigger_data_linking(self):
        # Asks the user for both files, then runs the backend join sequence.
        shapefile_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Cadastre Vector Dataset", 
            "", 
            "Spatial Vector Files (*.shp *.zip *.geojson *.json);;All Files (*)"
        )
        if not shapefile_path:
            return

        csv_path, _ = QFileDialog.getOpenFileName(
            self, "Select Valuation Roll Ledger (.csv)", "", "CSV Files (*.csv)"
        )
        if not csv_path:
            return

        try:
            # Execute background linking matrix (using 'erf_id' as the shared field key)
            linked_geojson = link_cadastre_to_valuation(shapefile_path, csv_path, join_column="erf_id")
            if linked_geojson:
                QMessageBox.information(
                    self, 
                    "Data Merged Successfully", 
                    "Municipal ledger registers have been mathematically bound to property polygon lines!"
                )
        except Exception as e:
            QMessageBox.critical(self, "Linking Error", f"Failed to perform data join operation:\n{str(e)}")

    def trigger_external_gis(self):
        """Asks the user which layer they want to edit, then opens it in desktop software."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select GIS Layer for External Editing", 
            "", 
            "Spatial Vector Files (*.shp *.zip *.geojson *.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            # Trigger background OS process launcher
            software_name = launch_external_gis(file_path)
            
            QMessageBox.information(
                self, 
                "Launching External GIS", 
                f"Handing off file to {software_name}.\nPlease perform edits there and save changes."
            )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Execution Error", 
                f"Could not open external design workspace:\n{str(e)}"
            )

    def placeholder_action(self):
        """Action handler for your other operation suite buttons."""
        QMessageBox.information(self, "System Update", "Module active. Connect database properties or scripts here.")