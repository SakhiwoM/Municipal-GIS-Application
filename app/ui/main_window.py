import os
import sys
import io
import json
import folium
import subprocess
import shutil
import platform
from PySide6.QtWidgets import QInputDialog
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFileDialog, QLabel, QMessageBox,
                             QFrame, QSplitter, QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QHeaderView, QLineEdit, QTabWidget,
                             QComboBox, QSizePolicy, QGridLayout)
from PySide6.QtCore import Qt, QObject, Signal, Slot, QCoreApplication, QPropertyAnimation, QEasingCurve, QStringListModel, QTimer, Property
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

try:
    from PySide6.QtWidgets import QCompleter
except ImportError:
    from PySide6.QtWidgets import QCompleter

# Safe import from app/core/
try:
    from app.core.import_cadastre import process_csv_to_geojson
    from app.core.link_data import link_cadastre_to_valuation
    from app.core.map_layers import add_base_layers, build_geojson_click_handler, inject_qwebchannel_bridge
    from app.core.spatial_utils import get_preferred_plot_title
    from app.core.edit_gis import launch_external_gis
except ImportError:
    def process_csv_to_geojson(file_path): return {"type": "FeatureCollection", "features": []}
    def link_cadastre_to_valuation(s, c, join_column): return {"type": "FeatureCollection", "features": []}
    def add_base_layers(leaflet_map, google_maps_api_key=None): return leaflet_map
    def build_geojson_click_handler(bridge_object_name="mapBridge", method_name="handleFeatureClick"): return None
    def inject_qwebchannel_bridge(leaflet_map, bridge_object_name="mapBridge"): return leaflet_map
    def get_preferred_plot_title(properties, feature_id=None): return str(feature_id) if feature_id is not None else "Selected Plot"
    def launch_external_gis(file_path): return "Fallback"


LIGHT_THEME = {
    "radius": "8px",
    "radius_sm": "5px",
    "bg": "#f0f4f8",
    "surface": "#f8fafc",
    "surface_alt": "#e4ecf6",
    "sidebar": "#004578",
    "sidebar_text": "#ffffff",
    "sidebar_muted": "#dbeafe",
    "card": "#ffffff",
    "accent": "#0071bc",
    "accent_dark": "#005a96",
    "accent_deep": "#004578",
    "text": "#1a2d3d",
    "text_muted": "#64748b",
    "border": "#d0dce8",
    "input_bg": "#ffffff",
    "divider": "#c8d6e5",
}

DARK_THEME = {
    "radius": "8px",
    "radius_sm": "5px",
    "bg":          "#0F172A",   # deep navy — outermost layer
    "surface":     "#172033",   # table/panel surfaces
    "surface_alt": "#1D2A3F",   # alternating rows / hover
    "sidebar":     "#111827",   # sidebar — lifted above bg
    "sidebar_text": "#ffffff",
    "sidebar_muted": "#bfdbfe",
    "card":        "#1E293B",   # cards — elevated from bg
    "accent":      "#3B82F6",   # vivid government blue
    "accent_dark": "#2563EB",
    "accent_deep": "#93C5FD",   # readable on dark surfaces
    "text":        "#E2E8F0",   # near-white, highly readable
    "text_muted":  "#94A3B8",   # secondary text — visible but quiet
    "border":      "#334155",   # subtle dividers
    "input_bg":    "#1A2332",   # inputs — distinct from cards
    "divider":     "#2A3A52",
}

THEME = LIGHT_THEME.copy()


class ToggleSwitch(QWidget):
    """Custom toggle switch widget with ON/OFF slider animation."""
    toggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._slide_position = 0.0
        self._animation = None
        self.setMinimumWidth(55)
        self.setMinimumHeight(26)
        self.setMaximumHeight(26)
        self.setCursor(Qt.PointingHandCursor)
        self.theme = LIGHT_THEME.copy()
    
    def setSlidePosition(self, value):
        """Set the slide position for animation."""
        self._slide_position = value
        self.update()
    
    def getSlidePosition(self):
        """Get the current slide position."""
        return self._slide_position
    
    # Register a Qt Property so QPropertyAnimation can animate it
    slide_position = Property(float, getSlidePosition, setSlidePosition)

    def resizeEvent(self, event):
        """Update slider position on resize so visual matches state."""
        super().resizeEvent(event)
        max_pos = max(0, self.width() - 22 - 4)
        if self._checked:
            self._slide_position = float(max_pos)
        else:
            self._slide_position = 0.0
        self.update()
    
    def setChecked(self, checked):
        """Set the toggle state and animate the slider."""
        if self._checked == checked:
            return
        self._checked = checked
        self._animate_toggle()
        self.toggled.emit(checked)
    
    def isChecked(self):
        """Return the current toggle state."""
        return self._checked
    
    def _animate_toggle(self):
        """Animate the slider position."""
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"slide_position")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Calculate max position (width - circle_diameter - padding)
        max_pos = self.width() - 22 - 4
        
        if self._checked:
            self._animation.setStartValue(0.0)
            self._animation.setEndValue(float(max_pos))
        else:
            self._animation.setStartValue(float(max_pos))
            self._animation.setEndValue(0.0)
        
        self._animation.start()
    
    def mousePressEvent(self, event):
        """Toggle on click."""
        self.setChecked(not self._checked)
    
    def paintEvent(self, event):
        """Paint the toggle switch."""
        from PySide6.QtGui import QPainter, QBrush, QPen, QFont
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get colors from theme
        if self._checked:
            bg_color = self.theme.get('accent', '#38bdf8')
            circle_color = '#ffffff'
            text_color = '#ffffff'
        else:
            bg_color = self.theme.get('text_muted', '#9ca3af')
            circle_color = '#ffffff'
            text_color = '#ffffff'
        
        # Draw background
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.setPen(QPen(Qt.NoPen))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height()//2, self.height()//2)
        
        # Draw circle slider
        circle_diameter = 22
        circle_y = (self.height() - circle_diameter) // 2
        painter.setBrush(QBrush(QColor(circle_color)))
        painter.drawEllipse(int(4 + self._slide_position), circle_y, circle_diameter, circle_diameter)
        
        # Draw text (small ON/OFF labels)
        painter.setPen(QPen(QColor(text_color)))
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)
        
        if self._checked:
            painter.drawText(2, 0, 26, self.height(), Qt.AlignCenter, "ON")
        else:
            painter.drawText(self.width() - 28, 0, 26, self.height(), Qt.AlignCenter, "OFF")


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
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)

        self.toggle_btn = QPushButton(f"▾  {title}")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME.get('sidebar_muted', THEME['text_muted'])};
                font-weight: 700;
                font-size: 12px;
                text-align: left;
                padding: 6px 2px;
                border: none;
                border-radius: 0;
                letter-spacing: 0.6px;
            }}
            QPushButton:hover {{ color: {THEME.get('sidebar_text', THEME['text'])}; }}
        """)
        self.toggle_btn.clicked.connect(self.toggle_menu)
        self.layout.addWidget(self.toggle_btn)

        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background-color: transparent; border: none;")
        self.content_frame.setMinimumHeight(0)
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(4, 2, 4, 2)
        self.content_layout.setSpacing(8)
        self.layout.addWidget(self.content_frame)

        self.is_expanded = True
        self.title_text = title

        self.toggle_animation = QPropertyAnimation(self.content_frame, b"maximumHeight")
        self.toggle_animation.setDuration(250)
        self.toggle_animation.setEasingCurve(QEasingCurve.InOutQuad)

    def toggle_menu(self):
        hint_height = self.content_layout.sizeHint().height()
        if self.is_expanded:
            self.toggle_animation.setStartValue(hint_height)
            self.toggle_animation.setEndValue(0)
            self.toggle_animation.start()
            self.toggle_btn.setText(f"▸  {self.title_text}")
        else:
            self.toggle_animation.setStartValue(0)
            self.toggle_animation.setEndValue(hint_height)
            self.toggle_animation.start()
            self.toggle_btn.setText(f"▾  {self.title_text}")
        self.is_expanded = not self.is_expanded

    def add_button(self, text, callback, color=None, hover_color=None, text_color=None):
        color = color or THEME["card"]
        hover_color = hover_color or THEME["surface"]
        text_color = text_color or THEME["text"]
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                font-size: 13px;
                padding: 7px 10px;
                border: 1px solid {THEME['border']};
                border-radius: {THEME['radius_sm']};
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border-left: 3px solid {THEME['accent']};
            }}
            QPushButton:pressed {{ background-color: {THEME['surface_alt']}; }}
        """)
        btn.clicked.connect(callback)
        self.content_layout.addWidget(btn)

        if self.is_expanded:
            self.content_frame.setMaximumHeight(self.content_layout.sizeHint().height() + 50)
        return btn

    def update_theme(self, theme):
        """Update CollapsibleMenu styles for the given theme."""
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.get('sidebar_muted', theme['text_muted'])};
                font-weight: 700;
                font-size: 12px;
                text-align: left;
                padding: 6px 2px;
                border: none;
                border-radius: 0;
                letter-spacing: 0.6px;
            }}
            QPushButton:hover {{ color: {theme.get('sidebar_text', theme['text'])}; }}
        """)
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                widget.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme['card']};
                        color: {theme['text']};
                        font-size: 13px;
                        padding: 7px 10px;
                        border: 1px solid {theme['border']};
                        border-radius: {theme['radius_sm']};
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        background-color: {theme['surface']};
                        border-left: 3px solid {theme['accent']};
                    }}
                    QPushButton:pressed {{ background-color: {theme['surface_alt']}; }}
                """)


class MainWindow(QMainWindow):
    logout_requested = Signal()

    def __init__(self, session=None):
        super().__init__()
        self.setWindowTitle("Eswatini Cadastre Workspace")
        self.resize(1350, 880)
        self.setMinimumSize(1050, 720)

        self.valuation_df = None
        self.current_geojson = None
        self.linked_geojson = None
        self.current_cadastre_file = None
        self.current_valuation_csv = None
        self.thematic_mode = "choropleth"   
        self._linked_ids_cache = set()       
        self._valuation_value_by_key = {}
        self._dashboard_row_source_indices = []
        self.current_theme_name = "light"
        self.theme = THEME
        self.session = session
        self._sidebar_section_labels = []
        self._sidebar_dividers = []

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {self.theme['bg']}; }}
            QToolTip {{
                background-color: {self.theme['accent_deep']};
                color: #ffffff;
                border: 1px solid {self.theme['accent_dark']};
                padding: 6px 10px;
                border-radius: {self.theme['radius_sm']};
            }}
            QScrollBar:vertical {{
                background: {self.theme['surface']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.theme['accent']};
                border-radius: 5px;
                min-height: 24px;
            }}
            QScrollBar:horizontal {{
                background: {self.theme['surface']};
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {self.theme['accent']};
                border-radius: 5px;
                min-width: 24px;
            }}
        """)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {self.theme['border']}; width: 4px; border-radius: 2px; }}")
        self.setCentralWidget(self.main_splitter)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setStyleSheet(f"""
            QWidget#Sidebar {{
                background-color: {self.theme['sidebar']};
                border-right: 1px solid {self.theme['accent_dark']};
            }}
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(6)

        # App identity block
        self.sidebar_title = QLabel("Eswatini GIS")
        self.sidebar_title.setStyleSheet(f"""
            font-weight: 800; font-size: 18px; letter-spacing: 0.3px;
            color: {self.theme.get('sidebar_text', self.theme['text'])}; margin-bottom: 0px;
        """)
        self.sidebar_subtitle = QLabel("Cadastre & Valuation Platform")
        self.sidebar_subtitle.setStyleSheet(f"""
            font-size: 12px; font-weight: 500;
            color: {self.theme.get('sidebar_muted', self.theme['text_muted'])}; margin-top: 0px; letter-spacing: 0.4px;
        """)
        sidebar_layout.addWidget(self.sidebar_title)
        sidebar_layout.addWidget(self.sidebar_subtitle)
        sidebar_layout.addWidget(self._make_sidebar_divider())
        if self.session:
            self.user_panel = self._make_user_panel()
            sidebar_layout.addWidget(self.user_panel)
            sidebar_layout.addWidget(self._make_sidebar_divider())

        # Search & Navigation
        sidebar_layout.addWidget(self._make_section_label("SEARCH & NAVIGATION"))
        self.setup_search_bar()
        sidebar_layout.addWidget(self.search_input)
        sidebar_layout.addWidget(self._make_sidebar_divider())

        # Appearance toggle
        theme_row = QHBoxLayout()
        theme_row.setContentsMargins(0, 0, 0, 0)
        theme_lbl = QLabel("Dark Mode")
        self.theme_label = theme_lbl
        theme_lbl.setStyleSheet(f"font-size: 13px; color: {self.theme.get('sidebar_muted', self.theme['text_muted'])}; font-weight: 600;")
        self.theme_toggle_btn = ToggleSwitch()
        self.theme_toggle_btn.theme = self.theme
        self.theme_toggle_btn.toggled.connect(self.toggle_theme_mode)
        theme_row.addWidget(theme_lbl)
        theme_row.addStretch()
        theme_row.addWidget(self.theme_toggle_btn)
        theme_row_w = QWidget()
        theme_row_w.setLayout(theme_row)
        theme_row_w.setStyleSheet("background: transparent;")
        sidebar_layout.addWidget(theme_row_w)
        sidebar_layout.addWidget(self._make_sidebar_divider())

        # Map Controls section
        sidebar_layout.addWidget(self._make_section_label("MAP CONTROLS"))
        self.map_mode_label = QLabel("Display Mode")
        self.map_mode_label.setStyleSheet(f"""
            font-size: 12px; font-weight: 700; color: {self.theme.get('sidebar_muted', self.theme['text_muted'])};
            letter-spacing: 0.4px;
        """)
        sidebar_layout.addWidget(self.map_mode_label)

        self.map_mode_combo = QComboBox()
        self.map_mode_combo.addItems(["Choropleth (Value Gradient)", "Link Status (Linked / Unlinked)"])
        self.map_mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme['card']};
                color: {self.theme['text']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme['card']};
                color: {self.theme['text']};
                selection-background-color: {self.theme['accent']};
                selection-color: #ffffff;
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
                padding: 4px;
            }}
        """)
        self.map_mode_combo.currentIndexChanged.connect(self._on_map_mode_changed)
        sidebar_layout.addWidget(self.map_mode_combo)

        self.legend_frame = QFrame()
        self.legend_frame.setStyleSheet(f"""
            background-color: {self.theme['surface']};
            border: 1px solid {self.theme['border']};
            border-radius: {self.theme['radius_sm']};
        """)
        legend_layout = QVBoxLayout(self.legend_frame)
        legend_layout.setContentsMargins(8, 6, 8, 6)
        legend_layout.setSpacing(3)
        self._legend_layout = legend_layout
        sidebar_layout.addWidget(self.legend_frame)
        self._rebuild_legend()
        sidebar_layout.addWidget(self._make_sidebar_divider())

        # Data Operations section
        self.menu_operations = CollapsibleMenu("DATA OPERATIONS")
        self.btn_import_cadastre = self.menu_operations.add_button("⬆  Import Cadastre", self.trigger_cadastre_import)
        self.btn_import_valuation = self.menu_operations.add_button("⬆  Import Valuation Roll", self.trigger_valuation_import)
        self.btn_link_data = self.menu_operations.add_button("⛓  Link Records", self.trigger_data_linking)
        self.menu_operations.add_button("⚙  Launch External GIS", self.trigger_external_gis)

        sidebar_layout.addWidget(self.menu_operations)
        sidebar_layout.addStretch()

        self.footer_lbl = QLabel("© 2026 Eswatini Municipal GIS")
        self.footer_lbl.setStyleSheet(f"color: {self.theme.get('sidebar_muted', self.theme['text_muted'])}; font-size: 11px;")
        sidebar_layout.addWidget(self.footer_lbl)

        self.main_splitter.addWidget(self.sidebar)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                border-top: 1px solid {self.theme['border']};
                background-color: {self.theme['bg']};
            }}
            QTabWidget::panel {{
                border: none;
                background-color: {self.theme['bg']};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {self.theme['text_muted']};
                padding: 9px 22px;
                font-weight: 600;
                font-size: 11px;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: transparent;
                color: {self.theme['accent']};
                border-bottom: 2px solid {self.theme['accent']};
                font-weight: 700;
            }}
            QTabBar::tab:hover {{
                background: {self.theme['surface']};
                color: {self.theme['text']};
                border-bottom: 2px solid {self.theme['divider']};
            }}
        """)
        self.main_splitter.addWidget(self.tabs)

        self.spatial_workspace = QSplitter(Qt.Horizontal)
        self.spatial_workspace.setStyleSheet(f"QSplitter::handle {{ background-color: {self.theme['border']}; width: 4px; border-radius: 2px; }}")

        self.map_view = QWebEngineView()
        self.map_view.setStyleSheet(f"""
            border: 1px solid {self.theme['border']};
            border-radius: {self.theme['radius']};
            background-color: {self.theme['bg']};
        """)
        self.map_bridge = MapClickBridge(self)
        self.web_channel = QWebChannel(self.map_view.page())
        self.web_channel.registerObject("mapBridge", self.map_bridge)
        self.map_view.page().setWebChannel(self.web_channel)
        self.map_bridge.featureSelected.connect(self.update_attribute_panel)
        self.eswatini_center = [-26.52, 31.46]
        self.spatial_workspace.addWidget(self.map_view)

        self.attribute_panel = QFrame()
        self.attribute_panel.setObjectName("AttrPanel")
        self.attribute_panel.setStyleSheet(f"""
            QFrame#AttrPanel {{
                background-color: {self.theme['card']};
                border-left: 1px solid {self.theme['border']};
                border-top-left-radius: {self.theme['radius']};
                border-bottom-left-radius: {self.theme['radius']};
            }}
        """)
        
        self.attribute_panel.setMinimumWidth(0)
        self.attribute_panel.setMaximumWidth(0)

        attribute_layout = QVBoxLayout(self.attribute_panel)
        attribute_layout.setContentsMargins(16, 16, 16, 16)
        attribute_layout.setSpacing(14)

        control_header_layout = QHBoxLayout()
        control_header_layout.addStretch()

        self.minimize_btn = QPushButton("—")
        self.minimize_btn.setFixedSize(26, 26)
        self.minimize_btn.setCursor(Qt.PointingHandCursor)
        self.minimize_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['surface']};
                border: 1px solid {self.theme['border']};
                font-size: 12px; font-weight: bold;
                color: {self.theme['text_muted']};
                border-radius: {self.theme['radius_sm']};
            }}
            QPushButton:hover {{ background-color: {self.theme['surface_alt']}; color: {self.theme['text']}; }}
        """)
        self.minimize_btn.clicked.connect(self.clear_attribute_panel)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['surface']};
                border: 1px solid {self.theme['border']};
                font-size: 10px; font-weight: bold;
                color: {self.theme['text_muted']};
                border-radius: {self.theme['radius_sm']};
            }}
            QPushButton:hover {{ background-color: #fee2e2; color: #ef4444; border-color: #fecaca; }}
        """)
        self.close_btn.clicked.connect(self.clear_attribute_panel)

        control_header_layout.addWidget(self.minimize_btn)
        control_header_layout.addWidget(self.close_btn)
        attribute_layout.addLayout(control_header_layout)

        self.attribute_title = QLabel("No plot selected")
        self.attribute_title.setWordWrap(False)  
        self.attribute_title.setStyleSheet(f"font-weight: 700; font-size: 16px; color: {self.theme['text']}; margin-top: 2px;")
        attribute_layout.addWidget(self.attribute_title)

        self.attribute_summary = QLabel("Click a plot on the map to view its attributes.")
        self.attribute_summary.setWordWrap(False)  
        self.attribute_summary.setStyleSheet(f"""
            color: {self.theme['accent_deep']};
            background-color: {self.theme['surface']};
            padding: 10px 14px;
            border-radius: {self.theme['radius_sm']};
            font-weight: 600;
            font-size: 11px;
            border: 1px solid {self.theme['border']};
        """)
        attribute_layout.addWidget(self.attribute_summary)

        self.attribute_table = QTableWidget(0, 2)
        self.attribute_table.setHorizontalHeaderLabels(["Attribute Field", "Value Data"])
        self.attribute_table.verticalHeader().setVisible(False)
        self.attribute_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.attribute_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.attribute_table.setAlternatingRowColors(True)
        self.attribute_table.setWordWrap(False)  
        self.attribute_table.setShowGrid(False)
        self.attribute_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  
        self.attribute_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.attribute_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.attribute_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.attribute_table.horizontalHeader().setStretchLastSection(True)
        
        self.attribute_table.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: {self.theme['card']}; 
                alternate-background-color: {self.theme['surface']}; 
                border: 1px solid {self.theme['border']}; 
                border-radius: {self.theme['radius_sm']}; 
                gridline-color: transparent; 
            }}
            QTableWidget::item {{ 
                padding: 10px 12px; 
                color: {self.theme['text']}; 
                font-size: 11px; 
                border-bottom: 1px solid {self.theme['surface_alt']}; 
            }}
            QHeaderView::section {{ 
                background-color: {self.theme['surface_alt']}; 
                color: {self.theme['accent_deep']}; 
                padding: 8px 12px; 
                font-weight: bold; 
                font-size: 11px; 
                border: none; 
                border-bottom: 2px solid {self.theme['border']}; 
            }}
        """)
        attribute_layout.addWidget(self.attribute_table)

        self.btn_generate_report = QPushButton("📄  Generate PDF Report")
        self.btn_generate_report.setCursor(Qt.PointingHandCursor)
        self.btn_generate_report.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_dark']};
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                padding: 11px 14px;
                border: none;
                border-radius: {self.theme['radius_sm']};
            }}
            QPushButton:hover {{ background-color: {self.theme['accent_deep']}; }}
            QPushButton:pressed {{ background-color: {self.theme['accent_dark']}; }}
        """)
        self.btn_generate_report.clicked.connect(self.generate_pdf_report)
        attribute_layout.addWidget(self.btn_generate_report)

        self.spatial_workspace.addWidget(self.attribute_panel)
        self.tabs.addTab(self.spatial_workspace, "Spatial Workspace")

        self.dashboard_widget = QWidget()
        self.dashboard_widget.setStyleSheet(f"background-color: {self.theme['bg']};")
        self.setup_dashboard_ui()
        self.tabs.addTab(self.dashboard_widget, "Analytics Dashboard")

        self.data_quality_widget = QWidget()
        self.data_quality_widget.setStyleSheet(f"background-color: {self.theme['bg']};")
        self.setup_data_quality_ui()
        self.tabs.addTab(self.data_quality_widget, "Data Quality")
        
        self.panel_animation = QPropertyAnimation(self.attribute_panel, b"maximumWidth")
        self.panel_animation.setDuration(280)
        self.panel_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.panel_animation.finished.connect(self._on_panel_animation_finished)

        self.clear_attribute_panel()
        self.main_splitter.setSizes([330, 1020])
        self.spatial_workspace.setSizes([1090, 0])

        self.map_view.page().loadFinished.connect(self._on_map_html_loaded)
        self.load_base_map(self.eswatini_center, starting_zoom=9)

    def _on_panel_animation_finished(self):
        if self.attribute_panel.maximumWidth() == 0:
            self.attribute_panel.hide()
        else:
            self.attribute_panel.setMaximumWidth(10000)

    def _rebuild_legend(self):
        while self._legend_layout.count():
            child = self._legend_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        title_lbl = QLabel("Legend")
        title_lbl.setStyleSheet(f"color: {self.theme['text_muted']}; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;")
        self._legend_layout.addWidget(title_lbl)

        if self.thematic_mode == "choropleth":
            entries = [
                ("#1e3a8a", "Premium (> 1M)"),
                ("#1d4ed8", "High (500k – 1M)"),
                ("#3b82f6", "Mid (100k – 500k)"),
                ("#60a5fa", "Low (< 100k)"),
                ("#93c5fd", "Unvalued / Zero"),
            ]
        else:
            entries = [
                ("#6366f1", "Linked (has valuation)"),
                ("#f97316", "Unlinked (no valuation)"),
            ]

        for color, label in entries:
            row = QHBoxLayout()
            swatch = QLabel()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(f"background-color: {color}; border-radius: 6px; border: 1px solid {self.theme['border']};")
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {self.theme['text']}; font-size: 12px;")
            row.addWidget(swatch)
            row.addWidget(lbl)
            row.addStretch()
            wrapper = QWidget()
            wrapper.setStyleSheet("background: transparent;")
            wrapper.setLayout(row)
            self._legend_layout.addWidget(wrapper)

    def _sync_thematic_mode_from_selection(self):
        selected_mode = self.map_mode_combo.currentText().lower()
        self.thematic_mode = (
            "link_status"
            if "link status" in selected_mode
            else "choropleth"
        )

    def refresh_map_display(self, overlay=None, starting_zoom=14):
        """Reload the map with colours matching the selected display mode."""
        self._sync_thematic_mode_from_selection()
        self._rebuild_legend()

        overlay = overlay or self.linked_geojson or self.current_geojson
        if not overlay:
            return

        center = self.eswatini_center
        bbox = overlay.get("bbox")
        if bbox and len(bbox) == 4:
            center = [(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2]

        self._rebuild_linked_ids_cache()
        self.load_base_map(
            center_coords=center,
            starting_zoom=starting_zoom,
            geojson_overlay=overlay,
        )

    def repaint_current_map_display(self):
        """Repaint the currently loaded Leaflet layers to match the display mode."""
        overlay = self.linked_geojson or self.current_geojson
        if not overlay:
            return

        self._rebuild_linked_ids_cache()
        payload = {
            "mode": self.thematic_mode,
            "linkedSet": list(self._linked_ids_cache),
            "choroplethMap": self._build_choropleth_color_map(overlay),
        }
        payload_json = json.dumps(payload)
        js = (
            f"if (typeof window.applyMapDisplayMode === 'function') "
            f"window.applyMapDisplayMode({payload_json});"
        )
        self.map_view.page().runJavaScript(js)
        if hasattr(self, "dash_map_view"):
            self.dash_map_view.page().runJavaScript(js)

    def _on_map_mode_changed(self, index):
        self._sync_thematic_mode_from_selection()
        self._rebuild_legend()
        self._rebuild_linked_ids_cache()
        if self.current_cadastre_file:
            self.reload_current_cadastre(silent=True)
        overlay = self.linked_geojson or self.current_geojson
        if overlay:
            self.repaint_current_map_display()

    def _on_map_html_loaded(self, ok=True):
        if ok and (self.linked_geojson or self.current_geojson):
            QTimer.singleShot(150, self.repaint_current_map_display)

    def _normalize_geojson_feature(self, feature):
        if not isinstance(feature, dict):
            return {"properties": {}}
        if "properties" in feature:
            return feature
        return {"properties": feature}

    def _make_user_panel(self):
        """Compact signed-in user card for the municipal workspace sidebar."""
        panel = QFrame()
        panel.setObjectName("UserPanel")
        panel.setStyleSheet(f"""
            QFrame#UserPanel {{
                background-color: {self.theme['card']};
                border: 1px solid {self.theme['border']};
                border-left: 3px solid {self.theme['accent']};
                border-radius: {self.theme['radius_sm']};
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        full_name = getattr(self.session, "full_name", "Signed-in User")
        role = getattr(self.session, "role", "user").replace("_", " ").title()
        organization = getattr(self.session, "organization", "Municipal Authority")

        self.user_name_lbl = QLabel(full_name)
        self.user_name_lbl.setStyleSheet(f"color: {self.theme['text']}; font-size: 13px; font-weight: 800;")
        self.user_role_lbl = QLabel(role)
        self.user_role_lbl.setStyleSheet(f"color: {self.theme['accent_deep']}; font-size: 12px; font-weight: 700;")
        self.user_org_lbl = QLabel(organization)
        self.user_org_lbl.setWordWrap(True)
        self.user_org_lbl.setStyleSheet(f"color: {self.theme['text_muted']}; font-size: 12px;")
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['surface_alt']};
                color: {self.theme['accent_deep']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
                padding: 7px 10px;
                font-size: 12px;
                font-weight: 800;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent']};
                color: #ffffff;
                border-color: {self.theme['accent_dark']};
            }}
        """)
        self.logout_btn.clicked.connect(self.request_logout)

        layout.addWidget(self.user_name_lbl)
        layout.addWidget(self.user_role_lbl)
        layout.addWidget(self.user_org_lbl)
        layout.addWidget(self.logout_btn)
        return panel

    def request_logout(self):
        if QMessageBox.question(
            self,
            "Logout",
            "Do you want to logout and return to the sign in page?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) == QMessageBox.Yes:
            self.logout_requested.emit()

    def _make_sidebar_divider(self):
        """Thin horizontal rule used as a visual separator in the sidebar."""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {self.theme.get('sidebar_muted', self.theme.get('divider', self.theme['border']))}; border: none; margin: 2px 0;")
        if hasattr(self, "_sidebar_dividers"):
            self._sidebar_dividers.append(line)
        return line

    def _make_section_label(self, text):
        """Small uppercase section label for sidebar grouping."""
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            font-size: 11px; font-weight: 800; letter-spacing: 0.8px;
            color: {self.theme.get('sidebar_muted', self.theme['text_muted'])}; padding: 2px 0 0 0;
        """)
        if hasattr(self, "_sidebar_section_labels"):
            self._sidebar_section_labels.append(lbl)
        return lbl

    def setup_search_bar(self):
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Plot ID, Owner, or keyword…")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 7px 10px;
                border-radius: {self.theme['radius_sm']};
                border: 1px solid {self.theme['border']};
                background: {self.theme['card']};
                color: {self.theme['text']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {self.theme['accent']};
                background: {self.theme['input_bg']};
            }}
        """)
        self._search_completer = QCompleter([], self.search_input)
        self._search_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._search_completer.setFilterMode(Qt.MatchContains)
        self._search_completer.setMaxVisibleItems(8)
        self.search_input.setCompleter(self._search_completer)
        self.search_input.textChanged.connect(self.perform_search)

    def update_search_completer(self):
        suggestions = set()
        geojson_to_index = self.linked_geojson or self.current_geojson
        if geojson_to_index:
            for feature in geojson_to_index.get("features", []):
                props = feature.get("properties", {}) or {}
                # Primary: 'text' property (used for linking with Portion Number)
                for key in ['text', 'TEXT', 'Text']:
                    val = props.get(key)
                    if val:
                        suggestions.add(str(val).strip())
                # Legacy ID fields as fallback
                for key in ['erf_id', 'no', 'plot_no', 'id', 'parcel_no', 'plot']:
                    val = props.get(key)
                    if val:
                        suggestions.add(str(val).strip())
                for key in ['owner', 'owner_name', "property owner's name", 'name']:
                    val = props.get(key)
                    if val:
                        suggestions.add(str(val).strip())
                if feature.get("id"):
                    suggestions.add(str(feature["id"]).strip())

        if self.valuation_df is not None:
            df = self.valuation_df
            type_col = no_col = ptn_col = None
            for col in df.columns:
                cl = str(col).strip().lower()
                if cl == 'type':   type_col = col
                elif cl == 'no':   no_col   = col
                elif cl == 'ptn':  ptn_col  = col

            for _, row in df.iterrows():
                # Constructed link key (e.g. "7/65", "R/10/65")
                if type_col and no_col:
                    key = self._build_valuation_link_key(
                        row.get(type_col, ''),
                        row.get(no_col, ''),
                        row.get(ptn_col, '') if ptn_col else '',
                    )
                    if key:
                        suggestions.add(key.strip())

                # Owner name for free-text search
                for col in df.columns:
                    if str(col).strip().lower() in ["property owner's name", 'owner', 'owner_name']:
                        v = str(row[col]).strip()
                        if v and v.lower() not in ('nan', ''):
                            suggestions.add(v)

        model = QStringListModel(sorted(suggestions), self._search_completer)
        self._search_completer.setModel(model)

    def perform_search(self, text):
        """Filters spatial features by querying Cadastre vector data AND Valuation records."""
        if not text or len(text) < 2:
            self.clear_map_highlights()
            return

        search_text = text.lower().strip()
        geojson_to_search = self.linked_geojson or self.current_geojson
        if not geojson_to_search:
            return

        # 1. Search directly inside Spatial GeoJSON features (all property values)
        for feature in geojson_to_search.get("features", []):
            properties = feature.get("properties", {}) or {}
            searchable_values = [str(v).lower().strip() for v in properties.values() if v]
            if feature.get("id"):
                searchable_values.append(str(feature["id"]).lower().strip())

            if any(search_text in val for val in searchable_values):
                self.zoom_to_feature(feature)
                return

        # 2. Search Valuation dataframe — resolve matching row → construct cadastre key
        if self.valuation_df is not None:
            df = self.valuation_df
            mask = df.astype(str).apply(lambda row: row.str.lower().str.contains(search_text).any(), axis=1)
            matching_rows = df[mask]
            if not matching_rows.empty:
                type_col = no_col = ptn_col = None
                for col in df.columns:
                    cl = str(col).strip().lower()
                    if cl == 'type':   type_col = col
                    elif cl == 'no':   no_col   = col
                    elif cl == 'ptn':  ptn_col  = col

                first = matching_rows.iloc[0]
                if type_col and no_col:
                    key = self._build_valuation_link_key(
                        first.get(type_col, ''),
                        first.get(no_col, ''),
                        first.get(ptn_col, '') if ptn_col else '',
                    )
                    if key:
                        self.zoom_to_plot_id(key.strip())

    def zoom_to_plot_id(self, plot_id):
        if not plot_id:
            return
        geojson_to_search = self.linked_geojson or self.current_geojson
        if not geojson_to_search:
            return

        plot_id_lower = plot_id.lower()
        for feature in geojson_to_search.get("features", []):
            properties = feature.get("properties", {}) or {}
            # Primary: match against cadastre 'text' property (original case — matches _linked_ids_cache)
            for key in ['text', 'TEXT', 'Text']:
                if properties.get(key) and str(properties[key]).strip() == plot_id:
                    self.zoom_to_feature(feature)
                    return
            # Fallback: case-insensitive for legacy ID fields
            for key in ['erf_id', 'no', 'plot_no', 'id', 'parcel_no', 'plot']:
                if properties.get(key) and str(properties[key]).strip().lower() == plot_id_lower:
                    self.zoom_to_feature(feature)
                    return
            if feature.get("id") and str(feature["id"]).strip().lower() == plot_id_lower:
                self.zoom_to_feature(feature)
                return

    def zoom_to_feature(self, feature):
        geometry = feature.get("geometry", {})
        if geometry and geometry.get("coordinates"):
            coords = geometry.get("coordinates")
            try:
                if geometry.get("type") == "Point":
                    lng, lat = coords[0], coords[1]
                elif geometry.get("type") in ["Polygon", "MultiPolygon"]:
                    ring = coords[0] if geometry.get("type") == "Polygon" else coords[0][0]
                    lat = sum(p[1] for p in ring) / len(ring)
                    lng = sum(p[0] for p in ring) / len(ring)
                else:
                    return

                js_code = (
                    f"(function(){{"
                    f"  var m = window.leaflet_map || window.map;"
                    f"  if (m) m.flyTo([{lat}, {lng}], 17, {{animate: true, duration: 0.8}});"
                    f"}})();"
                )
                self.tabs.setCurrentIndex(0)          # Switch to map tab first
                self.map_view.page().runJavaScript(js_code)
                if hasattr(self, "dash_map_view"):
                    self.dash_map_view.page().runJavaScript(js_code)
                self.highlight_feature_on_map(feature) # Highlight searched + linked shapes
                self.update_attribute_panel(feature)
            except Exception:
                pass

    def highlight_feature_on_map(self, feature):
        """Highlight the searched feature in yellow and all linked shapes in indigo.
        Calls the window.highlightSearchResult function injected into the Folium HTML."""
        props = feature.get("properties", {}) or {}
        text_val = ""
        for key in ["text", "TEXT", "Text"]:
            if props.get(key):
                text_val = str(props[key]).strip()
                break

        linked_list   = json.dumps(list(self._linked_ids_cache))
        text_val_json = json.dumps(text_val)

        js = (
            f"if (typeof window.highlightSearchResult === 'function') {{"
            f"  window.highlightSearchResult({text_val_json}, {linked_list}); "
            f"}}"
        )
        self.map_view.page().runJavaScript(js)
        if hasattr(self, "dash_map_view"):
            self.dash_map_view.page().runJavaScript(js)

    def clear_map_highlights(self):
        """Reset every map layer back to its current thematic style (no search highlight)."""
        self.repaint_current_map_display()

    def _get_feature_link_key(self, feature):
        props = feature.get("properties", {}) or {}
        for key in ["text", "TEXT", "Text", "text_value", "TEXT_VALUE", "Text_Value"]:
            value = props.get(key)
            if value not in (None, ""):
                return str(value).strip()

        for key in ["id", "ID", "no", "No", "NO", "erf_id", "plot_no", "parcel_no", "plot"]:
            value = props.get(key)
            if value not in (None, ""):
                bare = str(value).strip()
                if bare.endswith(".0") and bare[:-2].isdigit():
                    bare = bare[:-2]
                return bare

        feature_id = feature.get("id")
        if feature_id not in (None, ""):
            return str(feature_id).strip()
        return ""

    def _build_choropleth_color_map(self, geojson_overlay):
        color_map = {}
        for feature in geojson_overlay.get("features", []):
            text_key = self._get_feature_link_key(feature).lower()
            if text_key:
                color_map[text_key] = self.get_feature_color(feature)
        return color_map

    def _parse_numeric_value(self, value):
        if value in (None, ""):
            return 0.0
        cleaned = str(value).strip().replace(",", "")
        if cleaned.lower() in ("nan", "none", "-"):
            return 0.0
        return float(cleaned)

    def _get_property_case_insensitive(self, properties, names):
        normalized = {str(key).strip().lower(): value for key, value in properties.items()}
        for name in names:
            value = normalized.get(name.lower())
            if value not in (None, "", "nan", "NaN"):
                return value
        return None

    def feature_has_joined_valuation(self, feature):
        props = feature.get("properties", {}) or {}
        total_value = self._get_property_case_insensitive(
            props,
            ["Total Value", "total_value", "Value"],
        )
        if total_value not in (None, ""):
            return True

        owner = self._get_property_case_insensitive(
            props,
            ["Property Owner's Name", "owner", "owner_name"],
        )
        type_value = self._get_property_case_insensitive(props, ["Type"])
        no_value = self._get_property_case_insensitive(props, ["No"])
        return owner is not None or (type_value is not None and no_value is not None)

    def get_link_summary_counts(self, geojson_overlay=None):
        overlay = geojson_overlay or self.linked_geojson
        features = overlay.get("features", []) if overlay else []
        linked_count = sum(1 for feature in features if self.feature_has_joined_valuation(feature))
        total_count = len(features)
        return linked_count, total_count - linked_count, total_count

    def show_link_summary_popup(self, geojson_overlay=None):
        linked_count, unlinked_count, total_count = self.get_link_summary_counts(geojson_overlay)
        message = (
            "<p><b>Spatial data linking complete.</b></p>"
            f"<p>Total cadastre parcels checked: <b>{total_count:,}</b></p>"
            "<p>"
            "<span style='color:#6366f1; font-weight:700;'>■ Linked / matched valuation records:</span> "
            f"<b>{linked_count:,}</b><br>"
            "<span style='color:#f97316; font-weight:700;'>■ Unlinked / no valuation match:</span> "
            f"<b>{unlinked_count:,}</b>"
            "</p>"
            "<p>The map uses these same colors in Link Status display mode.</p>"
        )
        QMessageBox.information(self, "Link Spatial Data Summary", message)

    def get_feature_color(self, feature):
        try:
            feature = self._normalize_geojson_feature(feature)
            properties = feature.get("properties", {})
            val = self._get_property_case_insensitive(
                properties,
                ["Total Value", "total_value", "total value", "Value"],
            )
            if val in (None, ""):
                text_key = self._get_feature_link_key(feature)
                if text_key:
                    val = self._valuation_value_by_key.get(text_key.strip(), 0)
                else:
                    val = 0
            val = self._parse_numeric_value(val)
            if val == 0:
                return "#93c5fd"
            elif val < 100000:
                return "#60a5fa"
            elif val < 500000:
                return "#3b82f6"
            elif val < 1000000:
                return "#1d4ed8"
            else:
                return "#1e3a8a"
        except Exception:
            return "#93c5fd"

    def get_link_status_color(self, feature):
        """Return fill colour based on whether the cadastre 'text' field has a matching
        link key in the valuation roll cache.

        For FARM parcels the key is formatted e.g. "7/65", "R/10/65".
        For LOT/L/ERF parcels the key is the bare lot number e.g. "3".
        Both are stored as-is in _linked_ids_cache by _rebuild_linked_ids_cache.
        """
        try:
            feature = self._normalize_geojson_feature(feature)
            if self.feature_has_joined_valuation(feature):
                return "#6366f1"

            text_val = self._get_feature_link_key(feature)
            if text_val and text_val in self._linked_ids_cache:
                return "#6366f1"   # indigo = linked
            return "#f97316"   # orange = unlinked
        except Exception:
            return "#f97316"

    def _dashboard_filter_style(self):
        return f"""
            QLabel {{
                color: {self.theme['text_muted']};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
            QComboBox, QLineEdit {{
                background-color: {self.theme['input_bg']};
                color: {self.theme['text']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
                padding: 7px 10px;
                font-size: 11px;
                min-height: 18px;
            }}
            QComboBox:focus, QLineEdit:focus {{
                border-color: {self.theme['accent']};
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme['card']};
                color: {self.theme['text']};
                selection-background-color: {self.theme['accent']};
                selection-color: #ffffff;
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
            }}
        """

    def setup_dashboard_ui(self):
        dash_layout = QVBoxLayout(self.dashboard_widget)
        dash_layout.setContentsMargins(20, 20, 20, 20)
        dash_layout.setSpacing(16)

        header_row = QHBoxLayout()
        self.dash_title = QLabel("Analytics Dashboard")
        self.dash_title.setStyleSheet(f"""
            font-size: 20px; font-weight: 700; color: {self.theme['text']};
        """)
        self.dash_subtitle = QLabel("Filter, explore, and review cadastre & valuation records")
        self.dash_subtitle.setStyleSheet(f"font-size: 11px; color: {self.theme['text_muted']};")
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        header_text.addWidget(self.dash_title)
        header_text.addWidget(self.dash_subtitle)
        header_row.addLayout(header_text)
        header_row.addStretch()
        self.dashboard_filter_summary = QLabel("Showing 0 of 0 records")
        self.dashboard_filter_summary.setStyleSheet(f"""
            color: {self.theme['accent_deep']};
            font-size: 11px;
            font-weight: 700;
            background-color: {self.theme['card']};
            border: 1px solid {self.theme['border']};
            border-radius: {self.theme['radius_sm']};
            padding: 8px 14px;
        """)
        header_row.addWidget(self.dashboard_filter_summary)
        dash_layout.addLayout(header_row)

        self._kpi_cards_meta = []
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(14)
        self.lbl_cadastre_kpi = self.create_kpi_card("Total Cadastre Parcels", "0", "#0071bc", kpi_layout)
        self.lbl_valuation_kpi = self.create_kpi_card("Valuation Roll Records", "0", "#2563eb", kpi_layout)
        self.lbl_linked_kpi = self.create_kpi_card("Successfully Linked", "0", "#059669", kpi_layout)
        dash_layout.addLayout(kpi_layout)

        self.dashboard_filter_panel = QFrame()
        self.dashboard_filter_panel.setObjectName("DashboardFilterPanel")
        self.dashboard_filter_panel.setStyleSheet(f"""
            QFrame#DashboardFilterPanel {{
                background-color: {self.theme['card']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius']};
                padding: 12px;
            }}
            {self._dashboard_filter_style()}
        """)
        filter_outer = QVBoxLayout(self.dashboard_filter_panel)
        filter_outer.setContentsMargins(14, 12, 14, 12)
        filter_outer.setSpacing(10)

        filters_title = QLabel("Filters")
        filters_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.theme['text']};")
        filter_outer.addWidget(filters_title)

        filter_grid = QGridLayout()
        filter_grid.setContentsMargins(0, 0, 0, 0)
        filter_grid.setHorizontalSpacing(10)
        filter_grid.setVerticalSpacing(10)

        self.dashboard_link_filter = self._create_dashboard_filter_combo(
            filter_grid, 0, 0, "Link Status",
            ["All Records", "Linked Only", "Unlinked Only"],
        )
        self.dashboard_type_filter = self._create_dashboard_filter_combo(
            filter_grid, 0, 1, "Type", ["All Types"],
        )
        self.dashboard_use_filter = self._create_dashboard_filter_combo(
            filter_grid, 0, 2, "Use", ["All Uses"],
        )
        self.dashboard_status_filter = self._create_dashboard_filter_combo(
            filter_grid, 0, 3, "Status", ["All Statuses"],
        )
        self.dashboard_value_filter = self._create_dashboard_filter_combo(
            filter_grid, 1, 0, "Value Band",
            ["All Values", "Premium (> 1M)", "High (500k - 1M)", "Mid (100k - 500k)", "Low (< 100k)", "No Value"],
        )

        search_wrap = QVBoxLayout()
        search_label = QLabel("Search")
        self.dashboard_search_filter = QLineEdit()
        self.dashboard_search_filter.setPlaceholderText("Owner, parcel key, location...")
        search_wrap.addWidget(search_label)
        search_wrap.addWidget(self.dashboard_search_filter)
        filter_grid.addLayout(search_wrap, 1, 1, 1, 2)

        actions_wrap = QHBoxLayout()
        actions_wrap.setSpacing(8)
        self.dashboard_reset_filters_btn = QPushButton("Reset Filters")
        self.dashboard_reset_filters_btn.setCursor(Qt.PointingHandCursor)
        self.dashboard_reset_filters_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['surface_alt']};
                color: {self.theme['accent_deep']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
                padding: 9px 16px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent']};
                color: #ffffff;
                border-color: {self.theme['accent_dark']};
            }}
        """)
        actions_wrap.addWidget(self.dashboard_reset_filters_btn)
        filter_grid.addLayout(actions_wrap, 1, 3)

        filter_outer.addLayout(filter_grid)
        dash_layout.addWidget(self.dashboard_filter_panel)

        for combo in [
            self.dashboard_link_filter,
            self.dashboard_type_filter,
            self.dashboard_use_filter,
            self.dashboard_status_filter,
            self.dashboard_value_filter,
        ]:
            combo.currentIndexChanged.connect(self.update_dashboard_metrics)
        self.dashboard_search_filter.textChanged.connect(self.update_dashboard_metrics)
        self.dashboard_reset_filters_btn.clicked.connect(self.reset_dashboard_filters)

        self.dash_content_label = QLabel("Map & Data Table")
        self.dash_content_label.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.theme['text']};")
        dash_layout.addWidget(self.dash_content_label)

        self.dash_splitter = QSplitter(Qt.Vertical)
        self.dash_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {self.theme['border']};
                height: 6px;
                border-radius: 3px;
                margin: 4px 0;
            }}
        """)

        self.dash_map_view = QWebEngineView()
        self.dash_map_view.setStyleSheet(f"""
            border: 1px solid {self.theme['border']};
            border-radius: {self.theme['radius']};
            background-color: {self.theme['bg']};
        """)
        self.dash_map_view.page().loadFinished.connect(self._on_map_html_loaded)
        self.dash_splitter.addWidget(self.dash_map_view)

        self.dash_global_table = QTableWidget(0, 0)
        self.dash_global_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dash_global_table.setAlternatingRowColors(True)
        self.dash_global_table.setWordWrap(False)
        self.dash_global_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.dash_global_table.cellClicked.connect(self._on_dashboard_cell_clicked)
        self.dash_global_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme['card']};
                alternate-background-color: {self.theme['surface']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius']};
                gridline-color: transparent;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 9px 12px;
                font-size: 11px;
                color: {self.theme['text']};
                border-bottom: 1px solid {self.theme['surface_alt']};
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme['accent']};
                color: #ffffff;
            }}
            QTableWidget::item:hover {{
                background-color: {self.theme['surface_alt']};
            }}
            QHeaderView::section {{
                background-color: {self.theme['surface']};
                color: {self.theme['accent_deep']};
                padding: 9px 12px;
                font-weight: 700;
                font-size: 10px;
                letter-spacing: 0.3px;
                border: none;
                border-bottom: 2px solid {self.theme['accent']};
                border-right: 1px solid {self.theme['border']};
            }}
        """)
        self.dash_splitter.addWidget(self.dash_global_table)

        self.dash_splitter.setSizes([380, 280])
        dash_layout.addWidget(self.dash_splitter, 1)

    def _create_dashboard_filter_combo(self, parent_layout, row, col, label_text, items):
        wrapper = QVBoxLayout()
        wrapper.setSpacing(4)
        label = QLabel(label_text)
        combo = QComboBox()
        combo.addItems(items)
        wrapper.addWidget(label)
        wrapper.addWidget(combo)
        if isinstance(parent_layout, QGridLayout):
            parent_layout.addLayout(wrapper, row, col)
        else:
            parent_layout.addLayout(wrapper)
        return combo

    def reset_dashboard_filters(self):
        for combo in [
            self.dashboard_link_filter,
            self.dashboard_type_filter,
            self.dashboard_use_filter,
            self.dashboard_status_filter,
            self.dashboard_value_filter,
        ]:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.dashboard_search_filter.blockSignals(True)
        self.dashboard_search_filter.clear()
        self.dashboard_search_filter.blockSignals(False)
        self.update_dashboard_metrics()

    def _set_combo_options_preserving_selection(self, combo, default_label, values):
        current = combo.currentText()
        options = [default_label] + sorted(
            {
                str(value).strip()
                for value in values
                if value not in (None, "") and str(value).strip().lower() not in ("nan", "none")
            }
        )
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(options)
        combo.setCurrentIndex(options.index(current) if current in options else 0)
        combo.blockSignals(False)

    def _get_valuation_column_map(self, df):
        columns = {"type": None, "no": None, "ptn": None, "use": None, "status": None, "location": None, "total_value": None}
        for col in df.columns:
            normalized = str(col).strip().lower()
            if normalized in columns:
                columns[normalized] = col
            elif normalized in ("total value", "value"):
                columns["total_value"] = col
        return columns

    def _get_valuation_row_key(self, row, column_map):
        type_col = column_map.get("type")
        no_col = column_map.get("no")
        ptn_col = column_map.get("ptn")
        if not type_col or not no_col:
            return ""
        key = self._build_valuation_link_key(
            row.get(type_col, ""),
            row.get(no_col, ""),
            row.get(ptn_col, "") if ptn_col else "",
        )
        return key or ""

    def _is_valuation_row_linked(self, row, column_map, cadastre_text_vals):
        key = self._get_valuation_row_key(row, column_map)
        return bool(key and key.strip() in cadastre_text_vals)

    def _get_valuation_row_total_value(self, row, column_map):
        value_col = column_map.get("total_value")
        if not value_col:
            return 0.0
        try:
            return self._parse_numeric_value(row.get(value_col, 0))
        except Exception:
            return 0.0

    def _row_matches_value_filter(self, total_value, selected_filter):
        if selected_filter == "Premium (> 1M)":
            return total_value > 1000000
        if selected_filter == "High (500k - 1M)":
            return 500000 <= total_value <= 1000000
        if selected_filter == "Mid (100k - 500k)":
            return 100000 <= total_value < 500000
        if selected_filter == "Low (< 100k)":
            return 0 < total_value < 100000
        if selected_filter == "No Value":
            return total_value == 0
        return True

    def _dashboard_row_matches_filters(self, row, column_map, cadastre_text_vals):
        is_linked = self._is_valuation_row_linked(row, column_map, cadastre_text_vals)
        link_filter = self.dashboard_link_filter.currentText()
        if link_filter == "Linked Only" and not is_linked:
            return False
        if link_filter == "Unlinked Only" and is_linked:
            return False

        field_filters = [
            (self.dashboard_type_filter.currentText(), "type", "All Types"),
            (self.dashboard_use_filter.currentText(), "use", "All Uses"),
            (self.dashboard_status_filter.currentText(), "status", "All Statuses"),
        ]
        for selected, column_key, default_label in field_filters:
            col = column_map.get(column_key)
            if selected != default_label:
                value = "" if not col else str(row.get(col, "")).strip()
                if value != selected:
                    return False

        total_value = self._get_valuation_row_total_value(row, column_map)
        if not self._row_matches_value_filter(total_value, self.dashboard_value_filter.currentText()):
            return False

        search_text = self.dashboard_search_filter.text().strip().lower()
        if search_text:
            row_values = [str(value).lower() for value in row.values if value not in (None, "")]
            row_values.append(self._get_valuation_row_key(row, column_map).lower())
            if not any(search_text in value for value in row_values):
                return False

        return True

    def _cadastre_feature_matches_filters(self, feature):
        is_linked = self.feature_has_joined_valuation(feature)
        if not is_linked:
            text_val = self._get_feature_link_key(feature)
            if text_val and text_val in self._linked_ids_cache:
                is_linked = True

        link_filter = self.dashboard_link_filter.currentText()
        if link_filter == "Linked Only" and not is_linked:
            return False
        if link_filter == "Unlinked Only" and is_linked:
            return False

        props = feature.get("properties", {}) or {}
        field_filters = [
            (self.dashboard_type_filter.currentText(), ["Type", "type"], "All Types"),
            (self.dashboard_use_filter.currentText(), ["Use", "use"], "All Uses"),
            (self.dashboard_status_filter.currentText(), ["Status", "status"], "All Statuses"),
        ]
        for selected, names, default_label in field_filters:
            if selected != default_label:
                value = str(self._get_property_case_insensitive(props, names) or "").strip()
                if value != selected:
                    return False

        raw_value = self._get_property_case_insensitive(
            props,
            ["Total Value", "total_value", "total value", "Value"],
        ) or 0
        total_value = self._parse_numeric_value(raw_value)
        if not self._row_matches_value_filter(total_value, self.dashboard_value_filter.currentText()):
            return False

        search_text = self.dashboard_search_filter.text().strip().lower()
        if search_text:
            row_values = [str(value).lower() for value in props.values() if value not in (None, "")]
            feature_id = str(feature.get("id", "")).lower()
            if not any(search_text in value for value in row_values) and search_text not in feature_id:
                return False

        return True

    def create_kpi_card(self, title, initial_val, accent_color, parent_layout):
        if not hasattr(self, '_kpi_cards_meta'):
            self._kpi_cards_meta = []
        card = QFrame()
        card.setObjectName("KpiCard")
        card.setStyleSheet(f"""
            QFrame#KpiCard {{
                background-color: {self.theme['card']};
                border: 1px solid {self.theme['border']};
                border-top: 3px solid {accent_color};
                border-radius: {self.theme['radius']};
                padding: 16px 18px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(6)
        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(f"""
            font-size: 9px; font-weight: 700; color: {self.theme['text_muted']};
            letter-spacing: 0.5px;
        """)
        val_lbl = QLabel(initial_val)
        val_lbl.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {accent_color};")
        layout.addWidget(title_lbl)
        layout.addWidget(val_lbl)
        parent_layout.addWidget(card, 1)
        self._kpi_cards_meta.append({'frame': card, 'title_lbl': title_lbl, 'val_lbl': val_lbl, 'accent': accent_color})
        return val_lbl

    def _on_dashboard_cell_clicked(self, row, column):
        """Cross-dataset mapping: Clicking a row shifts the viewport focus to its geometry match."""
        if self.valuation_df is None:
            geojson_to_search = self.linked_geojson or self.current_geojson
            if geojson_to_search:
                features = geojson_to_search.get("features", [])
                source_row = self._dashboard_row_source_indices[row] if row < len(self._dashboard_row_source_indices) else row
                if source_row < len(features):
                    self.zoom_to_feature(features[source_row])
            return

        df = self.valuation_df
        source_row = self._dashboard_row_source_indices[row] if row < len(self._dashboard_row_source_indices) else row
        if source_row >= len(df):
            return

        column_map = self._get_valuation_column_map(df)
        plot_id = self._get_valuation_row_key(df.iloc[source_row], column_map)
        if plot_id:
            self.zoom_to_plot_id(plot_id.strip())

    def update_dashboard_metrics(self):
        cadastre_count = len(self.current_geojson.get("features", [])) if self.current_geojson else 0
        valuation_count = len(self.valuation_df) if self.valuation_df is not None else 0
        linked_count = 0
        if self.linked_geojson:
            linked_count = sum(
                1
                for feature in self.linked_geojson.get("features", [])
                if self.feature_has_joined_valuation(feature)
            )

        self.lbl_cadastre_kpi.setText(f"{cadastre_count:,}")
        self.lbl_valuation_kpi.setText(f"{valuation_count:,}")
        self.lbl_linked_kpi.setText(f"{linked_count:,}")

        self._rebuild_linked_ids_cache()

        # Build set of cadastre 'text' values for link-status comparison
        cadastre_text_vals = set()
        if self.current_geojson:
            for f in self.current_geojson.get("features", []):
                props = f.get("properties", {})
                for key in ['text', 'TEXT', 'Text']:
                    if key in props and props[key]:
                        cadastre_text_vals.add(str(props[key]).strip())
                        break

        if self.valuation_df is not None:
            import pandas as pd
            df = self.valuation_df
            column_map = self._get_valuation_column_map(df)

            self._set_combo_options_preserving_selection(
                self.dashboard_type_filter,
                "All Types",
                df[column_map["type"]].tolist() if column_map.get("type") else [],
            )
            self._set_combo_options_preserving_selection(
                self.dashboard_use_filter,
                "All Uses",
                df[column_map["use"]].tolist() if column_map.get("use") else [],
            )
            self._set_combo_options_preserving_selection(
                self.dashboard_status_filter,
                "All Statuses",
                df[column_map["status"]].tolist() if column_map.get("status") else [],
            )

            self.dash_global_table.setColumnCount(len(df.columns))
            self.dash_global_table.setHorizontalHeaderLabels(list(df.columns))

            filtered_rows = []
            self._dashboard_row_source_indices = []
            for source_idx, row in df.iterrows():
                if not self._dashboard_row_matches_filters(row, column_map, cadastre_text_vals):
                    continue
                filtered_rows.append((source_idx, row))
                self._dashboard_row_source_indices.append(source_idx)

            self.dash_global_table.setRowCount(len(filtered_rows))
            for display_idx, (_, row) in enumerate(filtered_rows):
                is_linked = self._is_valuation_row_linked(row, column_map, cadastre_text_vals)
                bg_color = QColor("#dbeafe") if is_linked else QColor("#ffedd5")

                for col_idx, value in enumerate(row):
                    val_str = "" if pd.isna(value) else str(value)
                    item = QTableWidgetItem(val_str)
                    item.setBackground(bg_color)
                    self.dash_global_table.setItem(display_idx, col_idx, item)
            self.dash_global_table.resizeColumnsToContents()
            self.dashboard_filter_summary.setText(f"Showing {len(filtered_rows):,} of {len(df):,} records")

        elif self.current_geojson:
            features = self.current_geojson.get("features", [])
            if features:
                sample_props = features[0].get("properties", {})
                headers = ["Feature ID"] + list(sample_props.keys())
                self.dash_global_table.setColumnCount(len(headers))
                self.dash_global_table.setHorizontalHeaderLabels(headers)

                filtered_features = []
                self._dashboard_row_source_indices = []
                for source_idx, feature in enumerate(features):
                    if not self._cadastre_feature_matches_filters(feature):
                        continue
                    filtered_features.append((source_idx, feature))
                    self._dashboard_row_source_indices.append(source_idx)

                self.dash_global_table.setRowCount(len(filtered_features))
                for display_idx, (_, feature) in enumerate(filtered_features):
                    fid = str(feature.get("id", ""))
                    self.dash_global_table.setItem(display_idx, 0, QTableWidgetItem(fid))
                    props = feature.get("properties", {})
                    for col_idx, key in enumerate(sample_props.keys(), start=1):
                        self.dash_global_table.setItem(
                            display_idx,
                            col_idx,
                            QTableWidgetItem(str(props.get(key, ""))),
                        )
                self.dash_global_table.resizeColumnsToContents()
                self.dashboard_filter_summary.setText(
                    f"Showing {len(filtered_features):,} of {len(features):,} records"
                )
            else:
                self.dash_global_table.setRowCount(0)
                self._dashboard_row_source_indices = []
                self.dashboard_filter_summary.setText("Showing 0 of 0 records")
        else:
            self.dash_global_table.setRowCount(0)
            self.dash_global_table.setColumnCount(0)
            self._dashboard_row_source_indices = []
            self.dashboard_filter_summary.setText("Showing 0 of 0 records")

        self.update_search_completer()

    # ------------------------------------------------------------------
    # Valuation ↔ Cadastre linking helpers
    # ------------------------------------------------------------------

    def _build_valuation_link_key(self, type_val, no_val, ptn_val):
        """Construct the cadastre 'text' key from valuation roll Type / No / Ptn fields.

        Eswatini cadastre text format examples
        ──────────────────────────────────────
          FARM 65  Ptn 7      → "7/65"          (simple portion)
          FARM 65  Ptn REM 10 → "R/10/65"       (remainder of a portion)
          FARM 45  Ptn REM    → "R/45"           (remainder of the whole farm)
          FARM 65  Ptn L1/28  → "L1/28/65"      (compound sub-lot – pass-through)
          FARM 65  Ptn R/A    → "R/A/65"         (lettered remainder – pass-through)
          LOT / L   No 3      → "3"              (LOT: direct No match)
        """
        t   = str(type_val).strip().upper()
        no  = str(no_val).strip()
        # Strip trailing .0 from numeric strings (e.g. "3.0" → "3")
        if no.endswith('.0') and no[:-2].isdigit():
            no = no[:-2]
        if not no or no.upper() in ('NAN', 'NONE'):
            return None
        ptn = str(ptn_val).strip()
        if ptn.endswith('.0'):
            ptn = ptn[:-2]
        pu  = ptn.upper()

        # LOT parcels: the cadastre 'text' field is just the lot number
        if t in ('LOT', 'L', 'ERF', 'E'):
            return no if no and no.upper() not in ('NAN', '', 'NONE') else None

        if pu in ('NAN', '', 'NONE'):
            return f"R/{no}"     # undivided remainder of the farm

        if pu == 'REM':
            return f"R/{no}"     # explicit "REM" = entire remaining extent

        if pu.startswith('REM'):
            # handles "REM 10", "REM10", "REM 4A" etc.
            suffix = pu[3:].strip()
            return f"R/{suffix}/{no}" if suffix else f"R/{no}"

        # All other cases (plain number, L1/28, R/A, R/6, …) just concat
        return f"{ptn}/{no}"

    def _rebuild_linked_ids_cache(self):
        """Build the set of normalised cadastre link-keys derived from the
        valuation roll's Type / No / Ptn columns so they can be matched
        against the cadastre GeoJSON 'text' property."""
        self._linked_ids_cache = set()
        self._valuation_value_by_key = {}
        if self.valuation_df is None:
            return

        df = self.valuation_df
        column_map = self._get_valuation_column_map(df)
        type_col = column_map.get("type")
        no_col = column_map.get("no")
        ptn_col = column_map.get("ptn")

        if type_col is None or no_col is None:
            return

        for _, row in df.iterrows():
            key = self._build_valuation_link_key(
                row.get(type_col, ''),
                row.get(no_col, ''),
                row.get(ptn_col, '') if ptn_col else '',
            )
            if key:
                key = key.strip()
                self._linked_ids_cache.add(key)
                self._valuation_value_by_key[key] = self._get_valuation_row_total_value(row, column_map)

    def load_base_map(self, center_coords, starting_zoom=9, geojson_overlay=None):
        self.clear_attribute_panel()
        leaflet_map = folium.Map(location=center_coords, zoom_start=starting_zoom, tiles=None, control_scale=True)
        add_base_layers(leaflet_map, google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"))
        inject_qwebchannel_bridge(leaflet_map)

        map_variable_name = leaflet_map.get_name()
        global_bridge_macro = f"window.leaflet_map = {map_variable_name}; window.map = {map_variable_name};"
        leaflet_map.get_root().script.add_child(folium.Element(global_bridge_macro))

        # ── JS helpers injected into every map page ────────────────────────────
        #
        # window._gisLinkedSet   – array of link-key strings kept in sync by Python
        # window._gisThematicMode – 'choropleth' | 'link_status'
        # window._gisChoroplethMap – text→color lookup for choropleth resets
        #
        # applyLinkStatusStyles()  – repaint all layers linked/unlinked
        # highlightSearchResult()  – yellow-highlight the searched shape, then
        #                            repaint everything else per current mode
        linked_list_json = json.dumps(list(self._linked_ids_cache))
        thematic_mode_js = json.dumps(self.thematic_mode)

        highlight_fn_js = f"""
window._gisLinkedSet    = {linked_list_json};
window._gisThematicMode = {thematic_mode_js};
window._gisChoroplethMap = {{}};   // populated on choropleth map loads

/* ── helper: get the best text key from a feature ─────────────────── */
window._gisGetTextKey = function(p) {{
    var tv = (p.text || p.TEXT || p.Text || p.text_value || p.TEXT_VALUE || p.Text_Value || '').toString().trim();
    if (tv) return tv;
    /* fallback for parcels with no text field */
    var id = (p.id || p.ID || p.no || p.No || p.NO || p.erf_id || p.plot_no || p.parcel_no || p.plot || '').toString().trim();
    if (id.match(/^[0-9]+[.]0$/)) id = id.slice(0, -2);
    return id;
}};

window._gisHasJoinedValuation = function(p) {{
    var keys = ['Total Value', 'total_value', 'Value', 'total value', "Property Owner's Name", 'owner', 'owner_name'];
    for (var i = 0; i < keys.length; i++) {{
        var v = p[keys[i]];
        if (v !== undefined && v !== null && String(v).trim() !== '' && String(v).toLowerCase() !== 'nan') {{
            return true;
        }}
    }}
    return false;
}};

window._gisIsFeatureLinked = function(p, linkedSet) {{
    var tv = window._gisGetTextKey(p);
    return (tv !== '' && linkedSet.indexOf(tv) >= 0) || window._gisHasJoinedValuation(p);
}};

/* ── repaint every layer according to link-status ─────────────────── */
window.applyLinkStatusStyles = function(linkedSet) {{
    var m = window.leaflet_map || window.map;
    if (!m) return;
    linkedSet = linkedSet || window._gisLinkedSet || [];
    m.eachLayer(function(layer) {{
        if (typeof layer.eachLayer !== 'function') return;
        layer.eachLayer(function(sl) {{
            if (!sl.feature) return;
            var p      = sl.feature.properties || {{}};
            var linked = window._gisIsFeatureLinked(p, linkedSet);
            sl.setStyle(linked
                ? {{ fillColor: '#6366f1', color: '#ffffff', weight: 1.5, fillOpacity: 0.72 }}
                : {{ fillColor: '#f97316', color: '#ffffff', weight: 1.5, fillOpacity: 0.65 }});
        }});
    }});
}};

/* ── highlight search result + repaint rest per current mode ──────── */
window.applyChoroplethStyles = function(colorMap) {{
    var m = window.leaflet_map || window.map;
    if (!m) return;
    colorMap = colorMap || window._gisChoroplethMap || {{}};
    m.eachLayer(function(layer) {{
        if (typeof layer.eachLayer !== 'function') return;
        layer.eachLayer(function(sl) {{
            if (!sl.feature) return;
            var p = sl.feature.properties || {{}};
            var tv = window._gisGetTextKey(p).toLowerCase();
            sl.setStyle({{ fillColor: colorMap[tv] || '#93c5fd', color: '#ffffff', weight: 1.5, fillOpacity: 0.6 }});
        }});
    }});
}};

window.applyMapDisplayMode = function(payload) {{
    payload = payload || {{}};
    window._gisThematicMode = payload.mode || window._gisThematicMode || 'choropleth';
    window._gisLinkedSet = payload.linkedSet || window._gisLinkedSet || [];
    window._gisChoroplethMap = payload.choroplethMap || window._gisChoroplethMap || {{}};
    if (window._gisThematicMode === 'link_status') {{
        window.applyLinkStatusStyles(window._gisLinkedSet);
    }} else {{
        window.applyChoroplethStyles(window._gisChoroplethMap);
    }}
}};

window.highlightSearchResult = function(searchTextVal, linkedSet) {{
    var m = window.leaflet_map || window.map;
    if (!m) return;
    linkedSet = linkedSet || window._gisLinkedSet || [];
    var mode  = window._gisThematicMode || 'choropleth';
    var cm    = window._gisChoroplethMap || {{}};
    m.eachLayer(function(layer) {{
        if (typeof layer.eachLayer !== 'function') return;
        layer.eachLayer(function(sl) {{
            if (!sl.feature) return;
            var p        = sl.feature.properties || {{}};
            var tv       = window._gisGetTextKey ? window._gisGetTextKey(p) : (p.text || p.TEXT || p.Text || '').toString().trim();
            var isSearched = (tv !== '' && tv === searchTextVal);
            var isLinked   = window._gisIsFeatureLinked(p, linkedSet);
            if (isSearched) {{
                sl.setStyle({{ fillColor: '#facc15', color: '#ea580c', weight: 3.5, fillOpacity: 0.92 }});
                if (typeof sl.bringToFront === 'function') sl.bringToFront();
            }} else if (mode === 'link_status') {{
                sl.setStyle(isLinked
                    ? {{ fillColor: '#6366f1', color: '#ffffff', weight: 1.5, fillOpacity: 0.72 }}
                    : {{ fillColor: '#f97316', color: '#ffffff', weight: 1.0, fillOpacity: 0.65 }});
            }} else {{
                var tvl = tv.toLowerCase();
                var fc  = cm[tvl] || '#93c5fd';
                sl.setStyle({{ fillColor: fc, color: '#ffffff', weight: 1.5, fillOpacity: 0.6 }});
            }}
        }});
    }});
}};

/* ── state variables are already baked into Python-rendered styles ──── */
/* JS vars kept in sync so highlightSearchResult / search work correctly. */
/* No auto-repaint needed — Python style_fn already applied correct colors. */
"""
        leaflet_map.get_root().script.add_child(folium.Element(highlight_fn_js))

        if geojson_overlay and geojson_overlay.get("features"):
            renderable_features = [f for f in geojson_overlay["features"] if f.get("geometry")]
            if renderable_features:
                renderable_geojson = dict(geojson_overlay)
                renderable_geojson["features"] = renderable_features

                if self.thematic_mode == "link_status":
                    style_fn = lambda feature, color_fn=self.get_link_status_color: {
                        "fillColor": color_fn(feature),
                        "color": "#ffffff",
                        "weight": 1.5,
                        "fillOpacity": 0.65,
                        "className": "animated-gis-path",
                    }
                else:
                    style_fn = lambda feature, color_fn=self.get_feature_color: {
                        "fillColor": color_fn(feature),
                        "color": "#ffffff",
                        "weight": 1.5,
                        "fillOpacity": 0.6,
                        "className": "animated-gis-path",
                    }

                geojson_layer = folium.GeoJson(
                    renderable_geojson,
                    name="Cadastre Layer",
                    style_function=style_fn,
                    highlight_function=lambda x: {"fillColor": "#a78bfa", "color": "#f97316", "weight": 3.0, "fillOpacity": 0.5},
                    on_each_feature=build_geojson_click_handler(),
                )
                geojson_layer.add_to(leaflet_map)

                # Populate window._gisChoroplethMap so JS highlight-reset works
                # without a Python round-trip when in choropleth mode.
                color_map = self._build_choropleth_color_map({"features": renderable_features})
                color_map_json = json.dumps(color_map)
                choropleth_inject_js = f"window._gisChoroplethMap = {color_map_json};"
                leaflet_map.get_root().script.add_child(folium.Element(choropleth_inject_js))

        folium.LayerControl(collapsed=False).add_to(leaflet_map)

        map_macro_header = """
        <style>
        @keyframes gisEntrance {
            0% { opacity: 0; transform: scale(0.96) translateY(10px); }
            100% { opacity: 1; transform: scale(1) translateY(0); }
        }
        .animated-gis-path { animation: gisEntrance 0.65s cubic-bezier(0.16, 1, 0.3, 1) both; transform-origin: center; }
        </style>
        """
        leaflet_map.get_root().header.add_child(folium.Element(map_macro_header))

        map_buffer = io.BytesIO()
        leaflet_map.save(map_buffer, close_file=False)
        map_html = map_buffer.getvalue().decode()

        self.map_view.setHtml(map_html)
        if hasattr(self, "dash_map_view"):
            self.dash_map_view.setHtml(map_html)
        QTimer.singleShot(200, self.repaint_current_map_display)

    def toggle_theme_mode(self, checked):
        """Toggle between light and dark theme."""
        if checked:
            self.current_theme_name = "dark"
            self.theme = DARK_THEME.copy()
        else:
            self.current_theme_name = "light"
            self.theme = LIGHT_THEME.copy()
        
        # Update theme reference in toggle button
        self.theme_toggle_btn.theme = self.theme
        self.apply_theme()

    def apply_theme(self):
        """Apply the current theme to all widgets."""
        # Main window
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {self.theme['bg']}; }}
            QToolTip {{
                background-color: {self.theme['accent_deep']};
                color: #ffffff;
                border: 1px solid {self.theme['accent_dark']};
                padding: 6px 10px;
                border-radius: {self.theme['radius_sm']};
            }}
            QScrollBar:vertical {{
                background: {self.theme['surface']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.theme['accent']};
                border-radius: 5px;
                min-height: 24px;
            }}
            QScrollBar:horizontal {{
                background: {self.theme['surface']};
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {self.theme['accent']};
                border-radius: 5px;
                min-width: 24px;
            }}
        """)

        # Sidebar and related widgets
        self.main_splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {self.theme['border']}; width: 4px; border-radius: 2px; }}")
        self.sidebar.setStyleSheet(f"""
            QWidget#Sidebar {{
                background-color: {self.theme['sidebar']};
                border-right: 1px solid {self.theme['accent_dark']};
            }}
        """)
        self.sidebar_title.setStyleSheet(f"""
            font-weight: 800; font-size: 18px; letter-spacing: 0.3px;
            color: {self.theme.get('sidebar_text', self.theme['text'])}; margin-bottom: 0px;
        """)
        if hasattr(self, 'sidebar_subtitle'):
            self.sidebar_subtitle.setStyleSheet(f"""
                font-size: 12px; font-weight: 500;
                color: {self.theme.get('sidebar_muted', self.theme['text_muted'])}; letter-spacing: 0.4px;
            """)
        if hasattr(self, 'user_panel'):
            self.user_panel.setStyleSheet(f"""
                QFrame#UserPanel {{
                    background-color: {self.theme['card']};
                    border: 1px solid {self.theme['border']};
                    border-left: 3px solid {self.theme['accent']};
                    border-radius: {self.theme['radius_sm']};
                }}
            """)
            self.user_name_lbl.setStyleSheet(f"color: {self.theme['text']}; font-size: 13px; font-weight: 800;")
            self.user_role_lbl.setStyleSheet(f"color: {self.theme['accent_deep']}; font-size: 12px; font-weight: 700;")
            self.user_org_lbl.setStyleSheet(f"color: {self.theme['text_muted']}; font-size: 12px;")
            self.logout_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme['surface_alt']};
                    color: {self.theme['accent_deep']};
                    border: 1px solid {self.theme['border']};
                    border-radius: {self.theme['radius_sm']};
                    padding: 7px 10px;
                    font-size: 12px;
                    font-weight: 800;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {self.theme['accent']};
                    color: #ffffff;
                    border-color: {self.theme['accent_dark']};
                }}
            """)
        # Update toggle button theme and internal state to match current theme
        try:
            is_dark = (self.current_theme_name == "dark")
            # set internal state without emitting to avoid re-entering toggle handler
            self.theme_toggle_btn._checked = is_dark
            max_pos = max(0, self.theme_toggle_btn.width() - 36 - 4)
            self.theme_toggle_btn._slide_position = float(max_pos) if is_dark else 0.0
        except Exception:
            pass
        self.theme_toggle_btn.theme = self.theme
        self.theme_toggle_btn.update()
        if hasattr(self, 'theme_label'):
            self.theme_label.setStyleSheet(f"font-size: 13px; color: {self.theme.get('sidebar_muted', self.theme['text_muted'])}; font-weight: 600;")
        if hasattr(self, '_sidebar_section_labels'):
            for label in self._sidebar_section_labels:
                label.setStyleSheet(f"""
                    font-size: 11px; font-weight: 800; letter-spacing: 0.8px;
                    color: {self.theme.get('sidebar_muted', self.theme['text_muted'])}; padding: 2px 0 0 0;
                """)
        if hasattr(self, '_sidebar_dividers'):
            for divider in self._sidebar_dividers:
                divider.setStyleSheet(f"background-color: {self.theme.get('sidebar_muted', self.theme.get('divider', self.theme['border']))}; border: none; margin: 2px 0;")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 7px 10px;
                border-radius: {self.theme['radius_sm']};
                border: 1px solid {self.theme['border']};
                background: {self.theme['card']};
                color: {self.theme['text']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {self.theme['accent']};
                background: {self.theme['input_bg']};
            }}
        """)
        self.map_mode_label.setStyleSheet(f"""
            font-size: 12px; font-weight: 700; color: {self.theme.get('sidebar_muted', self.theme['text_muted'])};
            letter-spacing: 0.4px;
        """)
        self.map_mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme['card']};
                color: {self.theme['text']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme['card']};
                color: {self.theme['text']};
                selection-background-color: {self.theme['accent']};
                selection-color: #ffffff;
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
                padding: 4px;
            }}
        """)
        self.legend_frame.setStyleSheet(f"""
            background-color: {self.theme['surface']};
            border: 1px solid {self.theme['border']};
            border-radius: {self.theme['radius_sm']};
        """)
        self.footer_lbl.setStyleSheet(f"color: {self.theme.get('sidebar_muted', self.theme['text_muted'])}; font-size: 11px;")

        # Tabs
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                border-top: 1px solid {self.theme['border']};
                background-color: {self.theme['bg']};
            }}
            QTabWidget::panel {{
                border: none;
                background-color: {self.theme['bg']};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {self.theme['text_muted']};
                padding: 9px 22px;
                font-weight: 600;
                font-size: 11px;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: transparent;
                color: {self.theme['accent']};
                border-bottom: 2px solid {self.theme['accent']};
                font-weight: 700;
            }}
            QTabBar::tab:hover {{
                background: {self.theme['surface']};
                color: {self.theme['text']};
                border-bottom: 2px solid {self.theme.get('divider', self.theme['border'])};
            }}
        """)

        # Spatial workspace
        self.spatial_workspace.setStyleSheet(f"QSplitter::handle {{ background-color: {self.theme['border']}; width: 4px; border-radius: 2px; }}")
        self.map_view.setStyleSheet(f"""
            border: 1px solid {self.theme['border']};
            border-radius: {self.theme['radius']};
            background-color: {self.theme['bg']};
        """)
        self.attribute_panel.setStyleSheet(f"""
            QFrame#AttrPanel {{
                background-color: {self.theme['card']};
                border-left: 1px solid {self.theme['border']};
                border-top-left-radius: {self.theme['radius']};
                border-bottom-left-radius: {self.theme['radius']};
            }}
        """)
        self.minimize_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['surface']};
                border: 1px solid {self.theme['border']};
                font-size: 12px; font-weight: bold;
                color: {self.theme['text_muted']};
                border-radius: {self.theme['radius_sm']};
            }}
            QPushButton:hover {{ background-color: {self.theme['surface_alt']}; color: {self.theme['text']}; }}
        """)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['surface']};
                border: 1px solid {self.theme['border']};
                font-size: 10px; font-weight: bold;
                color: {self.theme['text_muted']};
                border-radius: {self.theme['radius_sm']};
            }}
            QPushButton:hover {{ background-color: #fee2e2; color: #ef4444; border-color: #fecaca; }}
        """)
        self.attribute_title.setStyleSheet(f"font-weight: 700; font-size: 16px; color: {self.theme['text']}; margin-top: 2px;")
        self.attribute_summary.setStyleSheet(f"""
            color: {self.theme['accent_deep']};
            background-color: {self.theme['surface']};
            padding: 10px 14px;
            border-radius: {self.theme['radius_sm']};
            font-weight: 600;
            font-size: 11px;
            border: 1px solid {self.theme['border']};
        """)
        self.attribute_table.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: {self.theme['card']}; 
                alternate-background-color: {self.theme['surface']}; 
                border: 1px solid {self.theme['border']}; 
                border-radius: {self.theme['radius_sm']}; 
                gridline-color: transparent; 
            }}
            QTableWidget::item {{ 
                padding: 10px 12px; 
                color: {self.theme['text']}; 
                font-size: 11px; 
                border-bottom: 1px solid {self.theme['surface_alt']}; 
            }}
            QHeaderView::section {{ 
                background-color: {self.theme['surface_alt']}; 
                color: {self.theme['accent_deep']}; 
                padding: 8px 12px; 
                font-weight: bold; 
                font-size: 11px; 
                border: none; 
                border-bottom: 2px solid {self.theme['border']}; 
            }}
        """)
        self.btn_generate_report.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent_dark']};
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                padding: 11px 14px;
                border: none;
                border-radius: {self.theme['radius_sm']};
            }}
            QPushButton:hover {{ background-color: {self.theme['accent_deep']}; }}
            QPushButton:pressed {{ background-color: {self.theme['accent_dark']}; }}
        """)

        # Dashboard
        self.dashboard_widget.setStyleSheet(f"background-color: {self.theme['bg']};")
        self.dashboard_filter_summary.setStyleSheet(f"""
            color: {self.theme['accent_deep']};
            font-size: 11px;
            font-weight: 700;
            background-color: {self.theme['card']};
            border: 1px solid {self.theme['border']};
            border-radius: {self.theme['radius_sm']};
            padding: 8px 14px;
        """)
        self.dashboard_filter_panel.setStyleSheet(f"""
            QFrame#DashboardFilterPanel {{
                background-color: {self.theme['card']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius']};
                padding: 12px;
            }}
            QLabel {{
                color: {self.theme['text_muted']};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
            QComboBox, QLineEdit {{
                background-color: {self.theme['input_bg']};
                color: {self.theme['text']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
                padding: 7px 10px;
                font-size: 11px;
                min-height: 18px;
            }}
            QComboBox:focus, QLineEdit:focus {{
                border-color: {self.theme['accent']};
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme['card']};
                color: {self.theme['text']};
                selection-background-color: {self.theme['accent']};
                selection-color: #ffffff;
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
            }}
        """)
        self.dashboard_reset_filters_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['surface_alt']};
                color: {self.theme['accent_deep']};
                font-size: 11px;
                font-weight: bold;
                padding: 8px 12px;
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent']};
            }}
        """)
        self.dash_map_view.setStyleSheet(f"""
            border: 1px solid {self.theme['border']};
            border-radius: {self.theme['radius']};
            background-color: {self.theme['bg']};
        """)
        self.dash_global_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme['card']};
                alternate-background-color: {self.theme['surface']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius']};
                gridline-color: transparent;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 9px 12px;
                color: {self.theme['text']};
                font-size: 11px;
                border-bottom: 1px solid {self.theme['surface_alt']};
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme['accent']};
                color: #ffffff;
            }}
            QTableWidget::item:hover {{
                background-color: {self.theme['surface_alt']};
            }}
            QHeaderView::section {{
                background-color: {self.theme['surface']};
                color: {self.theme['accent_deep']};
                padding: 9px 12px;
                font-weight: 700;
                font-size: 10px;
                letter-spacing: 0.3px;
                border: none;
                border-bottom: 2px solid {self.theme['accent']};
                border-right: 1px solid {self.theme['border']};
            }}
        """)

        # Dashboard text labels
        if hasattr(self, 'dash_title'):
            self.dash_title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme['text']};")
        if hasattr(self, 'dash_subtitle'):
            self.dash_subtitle.setStyleSheet(f"font-size: 11px; color: {self.theme['text_muted']};")
        if hasattr(self, 'dash_content_label'):
            self.dash_content_label.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.theme['text']};")
        if hasattr(self, 'dash_splitter'):
            self.dash_splitter.setStyleSheet(f"""
                QSplitter::handle {{
                    background-color: {self.theme['border']};
                    height: 6px; border-radius: 3px; margin: 4px 0;
                }}
            """)

        # Analytics KPI card frames
        for meta in getattr(self, '_kpi_cards_meta', []):
            meta['frame'].setStyleSheet(f"""
                QFrame#KpiCard {{
                    background-color: {self.theme['card']};
                    border: 1px solid {self.theme['border']};
                    border-top: 3px solid {meta['accent']};
                    border-radius: {self.theme['radius']};
                }}
            """)
            meta['title_lbl'].setStyleSheet(
                f"font-size: 9px; font-weight: 700; color: {self.theme['text_muted']}; letter-spacing: 0.5px;"
            )

        self._apply_data_quality_theme()
        self.menu_operations.update_theme(self.theme)

    def _apply_data_quality_theme(self):
        """Re-apply theme to all Data Quality tab widgets."""
        if not hasattr(self, 'dq_header_title'):
            return
        self.data_quality_widget.setStyleSheet(f"background-color: {self.theme['bg']};")
        self.dq_header_title.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {self.theme['text']};"
        )
        if hasattr(self, 'dq_header_subtitle'):
            self.dq_header_subtitle.setStyleSheet(
                f"font-size: 11px; color: {self.theme['text_muted']};"
            )
        # DQ KPI cards
        for meta in getattr(self, '_dq_cards_meta', []):
            meta['frame'].setStyleSheet(f"""
                QFrame#DqKpiCard {{
                    background-color: {self.theme['card']};
                    border: 1px solid {self.theme['border']};
                    border-top: 3px solid {meta['accent']};
                    border-radius: {self.theme['radius']};
                }}
                QFrame#DqKpiCard:hover {{
                    border-color: {meta['accent']};
                    border-top-color: {meta['accent']};
                }}
            """)
            meta['title_lbl'].setStyleSheet(
                f"color: {self.theme['text_muted']}; font-size: 9px; font-weight: 700; letter-spacing: 0.5px;"
            )
        # Splitter, selector, combo, table
        if hasattr(self, 'dq_body_splitter'):
            self.dq_body_splitter.setStyleSheet(
                f"QSplitter::handle {{ background-color: {self.theme['border']}; width: 4px; }}"
            )
        if hasattr(self, 'dq_selector_frame'):
            self.dq_selector_frame.setStyleSheet(f"""
                QFrame#DqSelectorFrame {{
                    background-color: {self.theme['card']};
                    border: 1px solid {self.theme['border']};
                    border-radius: {self.theme['radius']};
                }}
            """)
        if hasattr(self, 'dq_sel_title_lbl'):
            self.dq_sel_title_lbl.setStyleSheet(
                f"font-size: 9px; font-weight: 800; letter-spacing: 0.6px; color: {self.theme['text_muted']};"
            )
        if hasattr(self, 'rule_combo'):
            self.rule_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {self.theme['input_bg']};
                    color: {self.theme['text']};
                    border: 1px solid {self.theme['border']};
                    border-radius: {self.theme['radius_sm']};
                    padding: 7px 10px;
                    font-size: 11px;
                }}
                QComboBox::drop-down {{ border: none; }}
                QComboBox QAbstractItemView {{
                    background-color: {self.theme['card']};
                    color: {self.theme['text']};
                    selection-background-color: {self.theme['accent']};
                    selection-color: #ffffff;
                    border: 1px solid {self.theme['border']};
                }}
            """)
        if hasattr(self, 'quality_table'):
            self.quality_table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {self.theme['card']};
                    alternate-background-color: {self.theme['surface']};
                    border: 1px solid {self.theme['border']};
                    border-radius: {self.theme['radius']};
                    gridline-color: transparent;
                    outline: none;
                }}
                QTableWidget::item {{
                    padding: 9px 12px;
                    font-size: 11px;
                    color: {self.theme['text']};
                    border-bottom: 1px solid {self.theme['surface_alt']};
                }}
                QTableWidget::item:selected {{
                    background-color: {self.theme['accent']};
                    color: #ffffff;
                }}
                QHeaderView::section {{
                    background-color: {self.theme['surface']};
                    color: {self.theme['accent_deep']};
                    padding: 9px 12px;
                    font-weight: 700;
                    font-size: 10px;
                    letter-spacing: 0.3px;
                    border: none;
                    border-bottom: 2px solid {self.theme['accent']};
                    border-right: 1px solid {self.theme['border']};
                }}
            """)

    def clear_attribute_panel(self):
        self.attribute_title.setText("No plot selected")
        self.attribute_summary.setText("Click a plot on the map to view its attributes.")
        self.attribute_table.setRowCount(0)
        
        if hasattr(self, 'panel_animation'):
            self.panel_animation.stop()
            self.panel_animation.setStartValue(self.attribute_panel.width())
            self.panel_animation.setEndValue(0)
            self.panel_animation.start()
        else:
            self.attribute_panel.hide()

    def update_attribute_panel(self, feature_data):
        if self.attribute_panel.maximumWidth() == 0 or self.attribute_panel.isHidden():
            self.attribute_panel.show()
            self.panel_animation.stop()
            self.panel_animation.setStartValue(self.attribute_panel.width())
            self.panel_animation.setEndValue(420)
            self.panel_animation.start()

        properties = feature_data.get("properties") or {}
        geometry = feature_data.get("geometry") or {}
        geometry_type = geometry.get("type") or "Unknown"
        feature_id = feature_data.get("id")

        selected_title = get_preferred_plot_title(properties, feature_id=feature_id)
        self.attribute_title.setText(selected_title)
        self.attribute_summary.setText(f"◆ Spatial Record Type: {geometry_type.upper()}")

        display_properties = dict(properties)

        if self.valuation_df is not None:
            try:
                lookup_val = None
                for key_variant in ['erf_id', 'no', 'plot_no', 'id', 'parcel_no', 'plot']:
                    for p_key, p_val in display_properties.items():
                        if p_key.lower().strip() == key_variant:
                            lookup_val = p_val
                            break
                    if lookup_val is not None:
                        break

                if lookup_val is None and feature_id is not None:
                    lookup_val = feature_id

                if lookup_val is not None:
                    search_str = str(lookup_val).strip().lower()
                    match_col = None
                    for col in self.valuation_df.columns:
                        if str(col).lower().strip() in ['no', 'erf_id', 'id', 'plot_no', 'parcel_no']:
                            match_col = col
                            break

                    if match_col is not None:
                        matched_rows = self.valuation_df[
                            self.valuation_df[match_col].astype(str).str.strip().str.lower() == search_str
                        ]
                        if not matched_rows.empty:
                            row_data = matched_rows.iloc[0]
                            for col_name, col_val in row_data.items():
                                display_key = str(col_name).strip()
                                if display_key.lower() != match_col.lower() and display_key not in display_properties:
                                    display_properties[display_key] = col_val
            except Exception:
                pass

        rows = [
            ("Plot Label Title", self.format_attribute_value(selected_title)),
            ("Global Feature ID", self.format_attribute_value(feature_id)),
            ("Vector Geometry", self.format_attribute_value(geometry_type)),
        ]
        for field_name, field_value in display_properties.items():
            rows.append((field_name, self.format_attribute_value(field_value)))

        self.attribute_table.setRowCount(len(rows))
        for row_index, (field_name, field_value) in enumerate(rows):
            field_item = QTableWidgetItem(f"  {field_name}")
            value_item = QTableWidgetItem(str(field_value))
            
            field_item.setForeground(QColor("#0f172a"))
            field_item.setFlags(field_item.flags() & ~Qt.ItemIsEditable)
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            
            self.attribute_table.setItem(row_index, 0, field_item)
            self.attribute_table.setItem(row_index, 1, value_item)

        self._current_feature_for_report = {
            "title": selected_title,
            "feature_id": feature_id,
            "geometry_type": geometry_type,
            "properties": display_properties,
        }

        self.attribute_table.resizeColumnsToContents()
        self.attribute_table.scrollToTop()

    @staticmethod
    def format_attribute_value(value):
        if value is None or value == "":
            return "-"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def generate_pdf_report(self):
        if not hasattr(self, "_current_feature_for_report") or not self._current_feature_for_report:
            QMessageBox.warning(self, "No Plot Selected", "Please click a plot on the map first.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Property Profile Report", "", "PDF Files (*.pdf)"
        )
        if not save_path:
            return
        if not save_path.lower().endswith(".pdf"):
            save_path += ".pdf"

        data = self._current_feature_for_report
        title = data.get("title", "Unknown Plot")
        feature_id = data.get("feature_id", "-")
        geometry_type = data.get("geometry_type", "-")
        properties = data.get("properties", {})

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.enums import TA_LEFT, TA_CENTER

            doc = SimpleDocTemplate(
                save_path,
                pagesize=A4,
                leftMargin=2 * cm,
                rightMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )
            styles = getSampleStyleSheet()

            header_style = ParagraphStyle(
                "ReportHeader",
                parent=styles["Normal"],
                fontSize=18,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1e3a8a"),
                spaceAfter=4,
            )
            sub_style = ParagraphStyle(
                "ReportSub",
                parent=styles["Normal"],
                fontSize=10,
                fontName="Helvetica",
                textColor=colors.HexColor("#64748b"),
                spaceAfter=2,
            )
            label_style = ParagraphStyle(
                "Label",
                parent=styles["Normal"],
                fontSize=9,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0f172a"),
            )
            value_style = ParagraphStyle(
                "Value",
                parent=styles["Normal"],
                fontSize=9,
                fontName="Helvetica",
                textColor=colors.HexColor("#334155"),
            )

            story = []

            story.append(Paragraph("PROPERTY PROFILE REPORT", header_style))
            story.append(Paragraph("Eswatini Municipal GIS — Cadastre & Valuation System", sub_style))
            story.append(Paragraph(f"Generated: {__import__('datetime').datetime.now().strftime('%d %B %Y, %H:%M')}", sub_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1d4ed8"), spaceAfter=10))
            story.append(Spacer(1, 0.3 * cm))

            summary_data = [
                [Paragraph("Plot / Property Title", label_style), Paragraph(str(title), value_style)],
                [Paragraph("Feature ID", label_style), Paragraph(str(feature_id), value_style)],
                [Paragraph("Geometry Type", label_style), Paragraph(str(geometry_type), value_style)],
            ]
            priority_keys = ["Total Value", "total_value", "Value", "Land Value", "Improvements",
                             "Owner", "owner_name", "property owner's name"]
            for pk in priority_keys:
                for prop_key, prop_val in properties.items():
                    if prop_key.strip().lower() == pk.lower() and prop_val not in (None, "", "-"):
                        summary_data.append([
                            Paragraph(str(prop_key), label_style),
                            Paragraph(str(prop_val), value_style),
                        ])

            summary_table = Table(summary_data, colWidths=[5 * cm, 11 * cm])
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
                ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.5 * cm))

            story.append(Paragraph("FULL ATTRIBUTE RECORD", ParagraphStyle(
                "SectionHead", parent=styles["Normal"],
                fontSize=11, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1e3a8a"), spaceBefore=8, spaceAfter=6,
            )))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

            attr_rows = [[Paragraph("Attribute", label_style), Paragraph("Value", label_style)]]
            for field, value in properties.items():
                attr_rows.append([
                    Paragraph(str(field), value_style),
                    Paragraph(self.format_attribute_value(value), value_style),
                ])

            attr_table = Table(attr_rows, colWidths=[6 * cm, 10 * cm])
            attr_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(attr_table)
            story.append(Spacer(1, 0.5 * cm))

            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=8))
            story.append(Paragraph(
                "This report is generated automatically by the Eswatini Cadastre GIS Workspace. "
                "For official valuations, refer to the current Valuation Roll.",
                ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8,
                               textColor=colors.HexColor("#94a3b8"), alignment=TA_CENTER),
            ))

            doc.build(story)
            QMessageBox.information(self, "Report Generated", f"Property profile saved to:\n{save_path}")

        except ImportError:
            QMessageBox.critical(
                self, "Missing Dependency",
                "ReportLab is required to generate PDF reports.\nInstall it with: pip install reportlab"
            )
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate report:\n{str(e)}")

    def reload_current_cadastre(self, silent=False):
        if not self.current_cadastre_file:
            return False
        try:
            geojson_data = process_csv_to_geojson(self.current_cadastre_file)
            self.current_geojson = geojson_data
            self.update_dashboard_metrics()
            self._rebuild_linked_ids_cache()
            if hasattr(self, 'refresh_quality_audit_table'):
                self.refresh_quality_audit_table()
            if geojson_data and geojson_data.get("features") and not self.linked_geojson:
                self.load_base_map(geojson_overlay=geojson_data)
            return True
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Cadastre Reload Error", str(e))
            return False

    def trigger_cadastre_import(self):
        import time
        from PySide6.QtWidgets import QProgressDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Cadastre Vector Dataset", "",
            "Spatial Vector Files (*.shp *.zip *.geojson *.json);;All Files (*)"
        )
        self.current_cadastre_file = file_path
        if not file_path:
            return

        progress = QProgressDialog("Reading and parsing spatial cadastre data...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(0)

        try:
            for step in range(1, 45):
                time.sleep(0.005)
                progress.setValue(step)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    return

            geojson_data = process_csv_to_geojson(file_path)
            self.current_geojson = geojson_data
            self.update_dashboard_metrics()

            for step in range(45, 101):
                time.sleep(0.005)
                progress.setValue(step)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    return

            progress.close()

            if geojson_data and geojson_data.get("features"):
                new_center = self.eswatini_center
                bbox = geojson_data.get("bbox")
                if bbox and len(bbox) == 4:
                    new_center = [(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2]
                self.load_base_map(center_coords=new_center, starting_zoom=14, geojson_overlay=geojson_data)
                
                QMessageBox.information(self, "Complete", f"Mapped {len(geojson_data['features'])} features. Use 'Link Spatial Data' to cross-link with the Valuation Roll.")
            if hasattr(self, 'refresh_quality_audit_table'):
             self.refresh_quality_audit_table()
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", str(e))

    def trigger_valuation_import(self):
        import time
        from PySide6.QtWidgets import QProgressDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Valuation Roll Dataset", "",
            "Excel/CSV Files (*.csv *.xlsx *.xls);;All Files (*)"
        )
        if not file_path:
            return

        progress = QProgressDialog("Reading and indexing valuation ledger data...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(0)

        try:
            for step in range(1, 60):
                time.sleep(0.005)
                progress.setValue(step)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    return

            import pandas as pd
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in ['.xlsx', '.xls']:
                df_raw = pd.read_excel(file_path, header=None)
            else:
                df_raw = pd.read_csv(file_path, header=None, encoding='utf-8', errors='replace')

            header_row_idx = 0
            for idx, row in df_raw.iterrows():
                row_strs = [str(val).strip().lower() for val in row.values if pd.notna(val)]
                if "property owner's name" in row_strs or ('type' in row_strs and 'no' in row_strs):
                    header_row_idx = idx
                    break

            if file_ext in ['.xlsx', '.xls']:
                self.valuation_df = pd.read_excel(file_path, skiprows=header_row_idx)
            else:
                self.valuation_df = pd.read_csv(file_path, skiprows=header_row_idx, encoding='utf-8', errors='replace')

            self.valuation_df.columns = [str(col).strip() for col in self.valuation_df.columns]
            self.current_valuation_csv = file_path
            self.update_dashboard_metrics()

            for step in range(60, 101):
                time.sleep(0.005)
                progress.setValue(step)
                QCoreApplication.processEvents()

            progress.close()

            self.btn_import_valuation.setText("Import Valuation Roll  ✓")
            self.btn_import_valuation.setStyleSheet("""
                QPushButton {
                    background-color: #065f46; color: #a7f3d0; font-size: 13px; padding: 10px 14px;
                    border: 1px solid #047857; border-radius: 6px; text-align: left; font-weight: bold;
                }
                QPushButton:hover { background-color: #047857; }
            """)
            
            QMessageBox.information(self, "Success", f"Loaded valuation roll:\n{os.path.basename(file_path)}\n\nUse 'Link Spatial Data' to cross-link with the Cadastre.")
            if hasattr(self, 'refresh_quality_audit_table'):
             self.refresh_quality_audit_table()
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Processing Error", f"Failed to register valuation roll:\n{str(e)}")

    def trigger_data_linking(self):
        shapefile_path = self.current_cadastre_file
        csv_path = self.current_valuation_csv

        if not shapefile_path or not csv_path:
            return

        if hasattr(self, 'btn_link_data'):
            self.btn_link_data.setText("Linking Data... Please Wait")
            self.btn_link_data.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b; color: white; font-weight: bold;
                    border: 1px solid #d97706; border-radius: 6px; text-align: left; padding: 10px; font-size: 13px;
                }
            """)
            QCoreApplication.processEvents()

        try:
            linked_geojson = link_cadastre_to_valuation(shapefile_path, csv_path, join_column="erf_id")

            if linked_geojson and linked_geojson.get("features"):
                self.linked_geojson = linked_geojson
                self.update_dashboard_metrics()
                self._sync_thematic_mode_from_selection()
                self._rebuild_legend()
                
                new_center = self.eswatini_center
                bbox = linked_geojson.get("bbox")
                if bbox and len(bbox) == 4:
                    new_center = [(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2]
                
                # Rebuild cache FIRST so Python style_fn uses correct colours
                self._rebuild_linked_ids_cache()
                # Full map reload — style_fn is evaluated synchronously by Python
                # with the populated cache, so colours are baked into the HTML.
                # No JS race conditions.
                self.load_base_map(
                    center_coords=new_center,
                    starting_zoom=14,
                    geojson_overlay=linked_geojson,
                )
                self.show_link_summary_popup(linked_geojson)

                if hasattr(self, 'btn_link_data'):
                    self.btn_link_data.setText("Linked Successfully ✓")
                    self.btn_link_data.setStyleSheet("""
                        QPushButton {
                            background-color: #065f46; color: #a7f3d0; font-weight: bold;
                            border: 1px solid #047857; border-radius: 6px; text-align: left; padding: 10px; font-size: 13px;
                        }
                    """)
            else:
                raise Exception("No matching records found between Cadastre and Valuation roll headers.")

        except Exception as e:
            if hasattr(self, 'btn_link_data'):
                self.btn_link_data.setText("Linking Sync Failed")
                self.btn_link_data.setStyleSheet("QPushButton { background-color: #ef4444; color: white; border-radius: 6px; padding: 10px; font-size: 13px; }")
            if hasattr(self, 'refresh_quality_audit_table'):
             self.refresh_quality_audit_table()
            QMessageBox.critical(self, "Linking Error", str(e))

    def setup_data_quality_ui(self):
        """Creates the grid overview and interactive audit table for the Data Quality Workspace."""
        from PySide6.QtWidgets import QGridLayout
        
        main_layout = QVBoxLayout(self.data_quality_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Header — matches Analytics Dashboard style
        dq_header_row = QHBoxLayout()
        self.dq_header_title = QLabel("Data Quality Audit")
        self.dq_header_title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme['text']};")
        self.dq_header_subtitle = QLabel("Automated audit checks across cadastre and valuation records")
        self.dq_header_subtitle.setStyleSheet(f"font-size: 11px; color: {self.theme['text_muted']};")
        dq_header_text = QVBoxLayout()
        dq_header_text.setSpacing(2)
        dq_header_text.addWidget(self.dq_header_title)
        dq_header_text.addWidget(self.dq_header_subtitle)
        dq_header_row.addLayout(dq_header_text)
        dq_header_row.addStretch()
        main_layout.addLayout(dq_header_row)

        # KPI cards grid — same design as Analytics Dashboard
        self.dq_grid_container = QFrame()
        self.dq_grid_container.setStyleSheet("background: transparent; border: none;")
        grid_layout = QGridLayout(self.dq_grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(14)

        self.quality_cards = {}
        self._dq_cards_meta = []
        rules = [
            ("Duplicate Parcel Numbers", "#ef4444"),
            ("Missing Owner Names",      "#f59e0b"),
            ("Missing Addresses",        "#3b82f6"),
            ("Invalid Plot Sizes",       "#059669"),
            ("Valuation Anomalies",      "#8b5cf6"),
            ("Geometry Errors",          "#ec4899"),
        ]

        for idx, (title, accent) in enumerate(rules):
            card = QFrame()
            card.setObjectName("DqKpiCard")
            card.setStyleSheet(f"""
                QFrame#DqKpiCard {{
                    background-color: {self.theme['card']};
                    border: 1px solid {self.theme['border']};
                    border-top: 3px solid {accent};
                    border-radius: {self.theme['radius']};
                }}
                QFrame#DqKpiCard:hover {{
                    border-color: {accent};
                    border-top-color: {accent};
                }}
            """)
            v_lay = QVBoxLayout(card)
            v_lay.setContentsMargins(16, 14, 16, 16)
            v_lay.setSpacing(6)

            lbl_title = QLabel(title.upper())
            lbl_title.setStyleSheet(
                f"color: {self.theme['text_muted']}; font-size: 9px; font-weight: 700; letter-spacing: 0.5px;"
            )
            lbl_val = QLabel("—")
            lbl_val.setStyleSheet(f"color: {accent}; font-size: 26px; font-weight: 700;")

            v_lay.addWidget(lbl_title)
            v_lay.addWidget(lbl_val)

            row = idx // 3
            col = idx % 3
            grid_layout.addWidget(card, row, col)
            self.quality_cards[title] = lbl_val
            self._dq_cards_meta.append({'frame': card, 'title_lbl': lbl_title, 'val_lbl': lbl_val, 'accent': accent})

        main_layout.addWidget(self.dq_grid_container)

        # Splitter Layout for Selector sidebar and details view
        self.dq_body_splitter = QSplitter(Qt.Horizontal)
        self.dq_body_splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {self.theme['border']}; width: 4px; }}"
        )

        # Sidebar rule selection panel
        self.dq_selector_frame = QFrame()
        self.dq_selector_frame.setObjectName("DqSelectorFrame")
        self.dq_selector_frame.setStyleSheet(f"""
            QFrame#DqSelectorFrame {{
                background-color: {self.theme['card']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius']};
            }}
        """)
        selector_layout = QVBoxLayout(self.dq_selector_frame)
        selector_layout.setContentsMargins(14, 14, 14, 14)
        selector_layout.setSpacing(10)

        self.dq_sel_title_lbl = QLabel("FILTER BY AUDIT RULE")
        self.dq_sel_title_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 800; letter-spacing: 0.6px; color: {self.theme['text_muted']};"
        )
        selector_layout.addWidget(self.dq_sel_title_lbl)

        self.rule_combo = QComboBox()
        for title, _ in rules:
            self.rule_combo.addItem(title)
        self.rule_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme['input_bg']};
                color: {self.theme['text']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius_sm']};
                padding: 7px 10px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme['card']};
                color: {self.theme['text']};
                selection-background-color: {self.theme['accent']};
                selection-color: #ffffff;
                border: 1px solid {self.theme['border']};
            }}
        """)
        self.rule_combo.currentTextChanged.connect(self.refresh_quality_audit_table)
        selector_layout.addWidget(self.rule_combo)
        selector_layout.addStretch()
        self.dq_selector_frame.setFixedWidth(220)
        self.dq_body_splitter.addWidget(self.dq_selector_frame)

        # Detailed Record Audit Log Grid
        self.quality_table = QTableWidget(0, 3)
        self.quality_table.setHorizontalHeaderLabels([
            "Parcel Key", "Issue Description", "Severity"
        ])
        self.quality_table.verticalHeader().setVisible(False)
        self.quality_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.quality_table.setAlternatingRowColors(True)
        self.quality_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.quality_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme['card']};
                alternate-background-color: {self.theme['surface']};
                border: 1px solid {self.theme['border']};
                border-radius: {self.theme['radius']};
                gridline-color: transparent;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 9px 12px;
                font-size: 11px;
                color: {self.theme['text']};
                border-bottom: 1px solid {self.theme['surface_alt']};
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme['accent']};
                color: #ffffff;
            }}
            QHeaderView::section {{
                background-color: {self.theme['surface']};
                color: {self.theme['accent_deep']};
                padding: 9px 12px;
                font-weight: 700;
                font-size: 10px;
                letter-spacing: 0.3px;
                border: none;
                border-bottom: 2px solid {self.theme['accent']};
                border-right: 1px solid {self.theme['border']};
            }}
        """)
        self.dq_body_splitter.addWidget(self.quality_table)
        main_layout.addWidget(self.dq_body_splitter)
        
        # Run initial population pipeline
        self.refresh_quality_audit_table(self.rule_combo.currentText())

    def refresh_quality_audit_table(self, rule_name=None):
        """Scans the live UI table data to generate real-time quality metrics."""
        if not hasattr(self, 'dash_global_table') or not hasattr(self, 'quality_table'):
            return

        if rule_name is None:
            rule_name = self.rule_combo.currentText() if hasattr(self, 'rule_combo') else "Duplicate Parcel Numbers"

        self.quality_table.setRowCount(0)
        
        duplicates = []
        missing_owners = []
        missing_addresses = []
        invalid_sizes = []
        valuation_anomalies = []
        geometry_errors = []

        seen_parcels = set()
        
        # Read headers from your actual table
        col_count = self.dash_global_table.columnCount()
        headers = [self.dash_global_table.horizontalHeaderItem(i).text().strip().lower() for i in range(col_count)]
        
        # Highly flexible index lookup matching any case or variations
        p_idx = next((i for i, h in enumerate(headers) if "parcel" in h or "id" in h or "key" in h), -1)
        o_idx = next((i for i, h in enumerate(headers) if "owner" in h or "name" in h), -1)
        a_idx = next((i for i, h in enumerate(headers) if "address" in h or "street" in h or "site" in h), -1)
        s_idx = next((i for i, h in enumerate(headers) if "size" in h or "area" in h or "plot" in h or "sqm" in h), -1)
        v_idx = next((i for i, h in enumerate(headers) if "val" in h or "price" in h or "amount" in h or "market" in h), -1)
        lat_idx = next((i for i, h in enumerate(headers) if "lat" in h or "y" in h), -1)
        lon_idx = next((i for i, h in enumerate(headers) if "lon" in h or "x" in h or "lng" in h), -1)

        total_rows = self.dash_global_table.rowCount()
        
        for row in range(total_rows):
            p_item = self.dash_global_table.item(row, p_idx) if p_idx != -1 else None
            parcel_id = p_item.text().strip() if p_item and p_item.text().strip() else f"Row {row + 1}"

            # 1. Duplicate Check
            if p_item:
                p_text = p_item.text().strip()
                if p_text:
                    if p_text in seen_parcels:
                        duplicates.append((p_text, "Duplicate parcel number found in database row entries", "High Severity"))
                    else:
                        seen_parcels.add(p_text)

            # 2. Missing Owner Names Check
            if o_idx != -1:
                o_item = self.dash_global_table.item(row, o_idx)
                if not o_item or o_item.text().strip() in ["", "N/A", "Unknown", "NaN", "null"]:
                    missing_owners.append((parcel_id, "Property entry has an unassigned or empty Owner field", "Medium Severity"))
            else:
                # If column isn't imported yet, classify it as unpopulated
                missing_owners.append((parcel_id, "Owner dataset has not been imported or linked yet", "Medium Severity"))

            # 3. Missing Addresses Check
            if a_idx != -1:
                a_item = self.dash_global_table.item(row, a_idx)
                if not a_item or a_item.text().strip() in ["", "N/A", "Unknown", "null"]:
                    missing_addresses.append((parcel_id, "Descriptive layout address or street index is blank", "Low Severity"))

            # 4. Invalid Plot Sizes Check
            if s_idx != -1:
                s_item = self.dash_global_table.item(row, s_idx)
                try:
                    val_str = s_item.text().replace(",", "").strip() if s_item else ""
                    val = float(val_str) if val_str else 0
                    if val <= 0:
                        invalid_sizes.append((parcel_id, f"Unusual plot dimensions listed: {val_str} sqm", "Medium Severity"))
                except ValueError:
                    invalid_sizes.append((parcel_id, "Plot area field contains unparsable text values", "Medium Severity"))

            # 5. Valuation Anomalies Check
            if v_idx != -1:
                v_item = self.dash_global_table.item(row, v_idx)
                try:
                    val_str = v_item.text().replace(",", "").replace("$", "").replace("R", "").strip() if v_item else ""
                    val = float(val_str) if val_str else 0
                    if val <= 0:
                        valuation_anomalies.append((parcel_id, "Asset is currently valued at 0 or unappraised", "High Severity"))
                except ValueError:
                    valuation_anomalies.append((parcel_id, "Valuation ledger contains non-numeric syntax errors", "High Severity"))
            else:
                # Prior to hitting the Link button, valuations won't exist in the dashboard layout
                valuation_anomalies.append((parcel_id, "Valuation pricing columns missing. Please execute Data Linkage.", "High Severity"))

            # 6. Geometry / Spatial Coordinates Check
            if lat_idx != -1 and lon_idx != -1:
                lat_item = self.dash_global_table.item(row, lat_idx)
                lon_item = self.dash_global_table.item(row, lon_idx)
                try:
                    lat = float(lat_item.text().strip()) if lat_item and lat_item.text().strip() else 0
                    lon = float(lon_item.text().strip()) if lon_item and lon_item.text().strip() else 0
                    if lat == 0 or lon == 0 or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                        geometry_errors.append((parcel_id, f"Invalid spatial coordinate boundaries mapping: ({lat}, {lon})", "Critical Severity"))
                except ValueError:
                    geometry_errors.append((parcel_id, "Spatial coordinate fields contain corrupted metadata types", "Critical Severity"))

        # Map rules to structural live lists
        live_audit_db = {
            "Duplicate Parcel Numbers": duplicates,
            "Missing Owner Names": missing_owners,
            "Missing Addresses": missing_addresses,
            "Invalid Plot Sizes": invalid_sizes,
            "Valuation Anomalies": valuation_anomalies,
            "Geometry Errors": geometry_errors
        }

        # Update summary counters dynamically
        if hasattr(self, 'quality_cards'):
            for title, key_lbl in self.quality_cards.items():
                count = len(live_audit_db.get(title, []))
                key_lbl.setText(f"{count} items detected")

        # Re-populate selected dashboard grid view
        active_rows = live_audit_db.get(rule_name, [])
        self.quality_table.setRowCount(len(active_rows))
        
        for r_idx, row_data in enumerate(active_rows):
            for c_idx, text_val in enumerate(row_data):
                item = QTableWidgetItem(str(text_val))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                
                # Apply threat clear alerts
                if c_idx == 2:
                    if "Critical" in str(text_val):
                        item.setForeground(QColor("#f43f5e"))
                    elif "High" in str(text_val):
                        item.setForeground(QColor("#fb923c"))
                        
                self.quality_table.setItem(r_idx, c_idx, item)

    def trigger_external_gis(self):
        """
        Launches external GIS software. Automatically picks the currently imported 
        cadastre dataset path if it exists. Otherwise, prompts the user to browse.
        """
        try:
            # 1. Automatically pick the file path imported by the import cadastre button
            if hasattr(self, "current_cadastre_file") and self.current_cadastre_file:
                file_path = self.current_cadastre_file
            else:
                # Fallback to manual selection if no file has been imported yet
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "Select GIS Layer", "", "Spatial Files (*.shp *.zip *.geojson *.gpkg)"
                )
                if not file_path:
                    return

            gis_apps = {
                "System Default": "system_default",
                "QGIS": r"C:\Program Files\QGIS 3.44.0\bin\qgis-bin.exe",
                "ArcGIS Pro": "arcgispro",
                "Google Earth Pro": "googleearth",
            }

            # 2. Setup and style the input dialog window to match the system theme properties
            dialog = QInputDialog(self)
            dialog.setWindowTitle("Open in External GIS")
            dialog.setLabelText("Select the compatible software to open this file:")
            dialog.setComboBoxItems(list(gis_apps.keys()))
            dialog.setComboBoxEditable(False)
            
            # Apply corporate system palette styles matching LIGHT/DARK active definitions
            dialog.setStyleSheet(f"""
                QInputDialog {{
                    background-color: {self.theme['bg']};
                }}
                QLabel {{
                    color: {self.theme['text']};
                    font-size: 12px;
                    font-weight: 600;
                }}
                QComboBox {{
                    background-color: {self.theme['card']};
                    color: {self.theme['text']};
                    border: 1px solid {self.theme['border']};
                    border-radius: {self.theme['radius_sm']};
                    padding: 8px 12px;
                    font-size: 12px;
                    min-width: 200px;
                }}
                QComboBox::drop-down {{
                    border: none;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {self.theme['card']};
                    color: {self.theme['text']};
                    selection-background-color: {self.theme['accent']};
                    selection-color: #ffffff;
                    border: 1px solid {self.theme['border']};
                }}
                QPushButton {{
                    background-color: {self.theme['surface_alt']};
                    color: {self.theme['accent_deep']};
                    font-size: 12px;
                    font-weight: bold;
                    padding: 8px 16px;
                    border: 1px solid {self.theme['border']};
                    border-radius: {self.theme['radius_sm']};
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme['accent']};
                    color: #ffffff;
                    border-color: {self.theme['accent_dark']};
                }}
                QPushButton:pressed {{
                    background-color: {self.theme['surface_alt']};
                }}
            """)

            if dialog.exec() == QInputDialog.Accepted:
                choice = dialog.textValue()
                if choice == "System Default":
                    if platform.system() == "Windows":
                        os.startfile(file_path)
                    elif platform.system() == "Darwin":
                        subprocess.call(['open', file_path])
                    else:
                        subprocess.call(['xdg-open', file_path])
                else:
                    app_cmd = gis_apps[choice]
                    if shutil.which(app_cmd):
                        subprocess.Popen([app_cmd, file_path])
                        QMessageBox.information(self, "Launching", f"Opening {file_path} in {choice}...")
                    else:
                        QMessageBox.warning(
                            self, "Software Not Found",
                            f"Could not find '{app_cmd}' in system PATH. "
                            "Ensure the software is installed and added to your environment variables.",
                        )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
