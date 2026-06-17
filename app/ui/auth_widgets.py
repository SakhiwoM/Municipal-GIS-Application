from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


def make_window_adjustable(window, width, height, min_width=None, min_height=None):
    window.resize(width, height)
    window.setMinimumSize(min_width or int(width * 0.72), min_height or int(height * 0.72))
    window.setWindowFlags(
        window.windowFlags()
        | Qt.WindowMinimizeButtonHint
        | Qt.WindowMaximizeButtonHint
    )


class EswatiniMapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(170)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = max(1, self.width())
        h = max(1, self.height())
        scale = min(w / 220, h / 250)
        ox = (w - 220 * scale) / 2
        oy = (h - 250 * scale) / 2

        def pt(x, y):
            return QPointF(ox + x * scale, oy + y * scale)

        path = QPainterPath()
        path.moveTo(pt(100, 8))
        for x, y in [
            (125, 20), (142, 48), (137, 75), (156, 102), (143, 126),
            (153, 154), (134, 178), (130, 211), (105, 241), (80, 225),
            (69, 195), (53, 177), (63, 145), (47, 116), (65, 88),
            (58, 55), (80, 35), (88, 16), (100, 8),
        ]:
            path.lineTo(pt(x, y))

        shadow = QPainterPath(path)
        painter.translate(5 * scale, 8 * scale)
        painter.fillPath(shadow, QColor(0, 0, 0, 42))
        painter.translate(-5 * scale, -8 * scale)

        painter.fillPath(path, QColor("#dbeafe"))
        painter.setPen(QPen(QColor("#ffffff"), max(2, int(2 * scale))))
        painter.drawPath(path)

        painter.setPen(QPen(QColor("#0071bc"), max(2, int(3 * scale))))
        painter.drawLine(pt(73, 70), pt(139, 70))
        painter.drawLine(pt(62, 127), pt(149, 127))
        painter.drawLine(pt(75, 187), pt(132, 187))

        painter.setPen(QPen(QColor("#ef4444"), max(2, int(4 * scale))))
        painter.drawEllipse(pt(101, 119), 6 * scale, 6 * scale)


class AuthBrandPanel(QFrame):
    def __init__(self, title, subtitle, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("BrandPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 34, 34, 34)
        layout.setSpacing(16)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("BrandTitle")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("BrandSubtitle")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        self.map_widget = EswatiniMapWidget()
        layout.addWidget(self.map_widget, 1)
        layout.addStretch()

