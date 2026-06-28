import sys
import os
import contextlib
import io

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette

with contextlib.redirect_stdout(io.StringIO()):
    from qfluentwidgets import (
        CaptionLabel, ComboBox, FluentIcon as FIF, InfoBar, InfoBarPosition,
        LineEdit, PushButton, SimpleCardWidget, SpinBox,
        StrongBodyLabel, Theme, setTheme, setThemeColor
    )
    from qfluentwidgets.components.widgets.combo_box import ComboBoxMenu


class BlueCardWidget(SimpleCardWidget):
    def _normalBackgroundColor(self):
        return QColor("#071426")

    def _hoverBackgroundColor(self):
        return QColor("#082044")

    def _pressedBackgroundColor(self):
        return QColor("#061225")

    def _disabledBackgroundColor(self):
        return QColor("#061225")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.backgroundColor)
        painter.setPen(QColor("#254A76"))
        radius = self.borderRadius
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)


COMBO_DROPDOWN_STYLE = """
MenuActionListWidget,
QListWidget#comboListWidget,
#comboListWidget {
    background-color: #061225;
    border: 1px solid #2E5688;
    border-radius: 8px;
    color: #F2F7FF;
    outline: none;
}
#comboListWidget::item {
    background-color: transparent;
    border-radius: 6px;
    color: #F2F7FF;
    margin: 3px 6px;
    padding: 7px 12px;
}
#comboListWidget::item:hover {
    background-color: #082044;
    color: #FFFFFF;
}
#comboListWidget::item:selected {
    background-color: #071B36;
    color: #FFFFFF;
    border-left: 3px solid #5B8CFF;
}
#comboListWidget::item:selected:active {
    background-color: #041022;
    color: #DDEAFF;
}
"""

OUTLINE_BUTTON_STYLE = """
PushButton,
QPushButton {
    background-color: #061225;
    border: 1px solid #2E5688;
    border-radius: 8px;
    color: #F2F7FF;
    padding: 7px 12px;
}
PushButton[hasIcon=true],
QPushButton[hasIcon=true] {
    padding-left: 34px;
}
PushButton:hover,
QPushButton:hover {
    background-color: #082044;
    border-color: #4978B8;
}
PushButton:pressed,
QPushButton:pressed {
    background-color: #041022;
    border-color: #5B8CFF;
}
"""

INLINE_TEXT_COLOR = QColor("#EAF3FF")
INLINE_PLACEHOLDER_COLOR = QColor("#AFC4E8")
INLINE_SELECTION_COLOR = QColor("#2F5C93")


def _resource_base_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    base_dir = Path(__file__).resolve().parent
    if base_dir.name.lower() == "source":
        return base_dir.parent
    return base_dir


class ThemedComboBox(ComboBox):
    def _createComboMenu(self):
        menu = ComboBoxMenu(self)
        menu.view.setStyleSheet(COMBO_DROPDOWN_STYLE)
        return menu


class AnimationGeneratorWindow(QMainWindow):
    def apply_theme(self, use_global_theme=True):
        app = QApplication.instance()
        if app is None:
            return

        if use_global_theme:
            setTheme(Theme.DARK)
            setThemeColor(QColor("#5B8CFF"))
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #070A12;
            }
            QWidget#page,
            QWidget#dialogPage {
                background-color: #070A12;
            }
            SimpleCardWidget#surfaceCard {
                background-color: #071426;
                border: 1px solid #23466F;
                border-radius: 14px;
            }
            QLabel {
                color: #EEF5FF;
            }
            QLabel#mutedLabel,
            QLabel#fieldLabel {
                color: #8FA2BD;
            }
            QLabel#pathLabel,
            QLabel#infoPanel,
            QLabel#progressLabel {
                background-color: #030914;
                border: 1px solid #254A76;
                border-radius: 10px;
                color: #DCE8F9;
                padding: 9px 11px;
            }
            QLabel#progressLabel {
                color: #DDE8FF;
                border-color: #356EAE;
                background-color: #071B36;
            }
            PushButton,
            QPushButton,
            ComboBox,
            QComboBox,
            LineEdit,
            QLineEdit,
            SpinBox,
            QSpinBox,
            QAbstractSpinBox {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #F2F7FF;
                padding: 7px 12px;
            }
            PushButton:hover,
            QPushButton:hover,
            ComboBox:hover,
            QComboBox:hover,
            LineEdit:hover,
            QLineEdit:hover,
            SpinBox:hover,
            QSpinBox:hover,
            QAbstractSpinBox:hover {
                background-color: #082044;
                border-color: #4978B8;
            }
            PushButton:pressed,
            QPushButton:pressed,
            ComboBox:pressed,
            QComboBox:pressed,
            SpinBox:pressed,
            QSpinBox:pressed {
                background-color: #041022;
                border-color: #5B8CFF;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            """
        )

    def _settings_row(self, label_text, widget):
        row_widget = QWidget()
        row_widget.setFixedHeight(46)

        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)

        label = CaptionLabel(label_text)
        label.setObjectName("fieldLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        label.setFixedWidth(125)

        widget.setFixedHeight(38)
        widget.setStyleSheet(
            widget.styleSheet() + """
            SpinBox,
            QSpinBox,
            QAbstractSpinBox,
            ComboBox {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #F2F7FF;
                padding: 7px 12px;
            }
            QComboBox {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #F2F7FF;
                padding: 7px 12px;
            }
            SpinBox:hover,
            QSpinBox:hover,
            QAbstractSpinBox:hover,
            ComboBox:hover {
                background-color: #082044;
                border-color: #4978B8;
            }
            QComboBox:hover {
                background-color: #082044;
                border-color: #4978B8;
            }
            SpinBox:focus {
                background-color: #061225;
                border-color: #5B8CFF;
            }
            QSpinBox:focus,
            QAbstractSpinBox:focus {
                background-color: #061225;
                border-color: #5B8CFF;
            }
            SpinBox[transparent=true]:focus,
            SpinBox[transparent=false]:focus {
                background-color: #061225;
                border: 1px solid #5B8CFF;
                border-bottom: 1px solid #5B8CFF;
                color: #FFFFFF;
            }
            ComboBox:pressed {
                background-color: #041022;
                border-color: #5B8CFF;
            }
            QComboBox:pressed {
                background-color: #041022;
                border-color: #5B8CFF;
            }
            """
        )
        row.addWidget(label)
        row.addWidget(widget, 1)
        return row_widget

    def _apply_inline_text_palette(self, widget):
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.Text, INLINE_TEXT_COLOR)
        palette.setColor(QPalette.ColorRole.ButtonText, INLINE_TEXT_COLOR)
        palette.setColor(QPalette.ColorRole.PlaceholderText, INLINE_PLACEHOLDER_COLOR)
        palette.setColor(QPalette.ColorRole.Highlight, INLINE_SELECTION_COLOR)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        widget.setPalette(palette)

        line_edit = widget.lineEdit() if hasattr(widget, "lineEdit") else None
        if line_edit is not None:
            line_edit.setPalette(palette)
            line_edit.setStyleSheet(
                """
                QLineEdit {
                    background-color: #061225;
                    border: none;
                    color: #EAF3FF;
                    padding: 0px 6px;
                    selection-background-color: #2F5C93;
                    selection-color: #FFFFFF;
                }
                QLineEdit:focus {
                    background-color: #061225;
                    border: none;
                    color: #FFFFFF;
                }
                """
            )

    def _blue_info(self, title, content, duration=3500):
        bar = InfoBar.new(
            FIF.INFO,
            title,
            content,
            parent=self,
            duration=duration,
            position=InfoBarPosition.TOP_RIGHT,
        )
        bar.setCustomBackgroundColor("#DCEBFF", "#082A54")
        bar.setStyleSheet(
            """
            InfoBar {
                border: 1px solid #4F8CFF;
                border-radius: 8px;
            }
            QLabel#titleLabel {
                color: #FFFFFF;
                font-weight: 700;
            }
            QLabel#contentLabel {
                color: #DDEAFF;
            }
            TransparentToolButton {
                color: #DDEAFF;
            }
            """
        )
        return bar

    def _outline_button(self, icon, text, height=38, width=None):
        button = PushButton(icon, text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(height)
        if width is not None:
            button.setFixedWidth(width)
        button.setStyleSheet(OUTLINE_BUTTON_STYLE)
        return button

    def __init__(self, use_global_theme=True):
        super().__init__()
        self.setWindowTitle("Login Animation XML Generator")
        self.set_icon()
        self.setMinimumSize(600, 500)
        self.resize(640, 520)
        self.apply_theme(use_global_theme=use_global_theme)

        central = QWidget()
        central.setObjectName("dialogPage")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        settings_card = BlueCardWidget()
        settings_card.setObjectName("surfaceCard")
        settings_card.setBackgroundColor(QColor("#071426"))
        settings_card.setBorderRadius(14)
        settings_card.setMinimumHeight(250)
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(22, 20, 22, 22)
        settings_layout.setSpacing(16)
        settings_layout.addWidget(StrongBodyLabel("Animation Settings"))

        self.spin_start = SpinBox()
        self.spin_start.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.spin_start.setRange(1, 9999)
        self.spin_start.setValue(1)
        self.spin_start.setSuffix("   ")
        self._apply_inline_text_palette(self.spin_start)
        settings_layout.addWidget(self._settings_row("Start frame:", self.spin_start))

        self.spin_end = SpinBox()
        self.spin_end.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.spin_end.setRange(1, 9999)
        self.spin_end.setValue(221)
        self.spin_end.setSuffix("   ")
        self._apply_inline_text_palette(self.spin_end)
        settings_layout.addWidget(self._settings_row("End frame:", self.spin_end))

        self.spin_fps = SpinBox()
        self.spin_fps.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.spin_fps.setRange(1, 120)
        self.spin_fps.setValue(30)
        self.spin_fps.setSuffix(" fps")
        self._apply_inline_text_palette(self.spin_fps)
        settings_layout.addWidget(self._settings_row("Frames per second:", self.spin_fps))

        self.combo_filter = ThemedComboBox()
        filters = ["nearest", "linear"]
        self.combo_filter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_filter.addItems(filters)
        self.combo_filter.setCurrentText("nearest")
        settings_layout.addWidget(self._settings_row("Scaling filter:", self.combo_filter))
        main_layout.addWidget(settings_card)

        path_card = BlueCardWidget()
        path_card.setObjectName("surfaceCard")
        path_card.setBackgroundColor(QColor("#071426"))
        path_card.setBorderRadius(14)
        path_outer = QVBoxLayout(path_card)
        path_outer.setContentsMargins(22, 20, 22, 22)
        path_outer.setSpacing(14)
        path_outer.addWidget(StrongBodyLabel("Output File"))

        path_layout = QHBoxLayout()
        path_layout.setSpacing(12)

        self.edit_path = LineEdit()
        self.edit_path.setPlaceholderText("Select where to save login-animation.xml")
        self.edit_path.setReadOnly(True)
        self.edit_path.setMinimumHeight(38)
        self._apply_inline_text_palette(self.edit_path)
        self.edit_path.setStyleSheet(
            self.edit_path.styleSheet() + """
            LineEdit {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #EAF3FF;
                placeholder-text-color: #BFD4F2;
                selection-background-color: #2F5C93;
                selection-color: #FFFFFF;
                padding: 7px 12px;
            }
            QLineEdit {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #EAF3FF;
                placeholder-text-color: #BFD4F2;
                selection-background-color: #2F5C93;
                selection-color: #FFFFFF;
                padding: 7px 12px;
            }
            LineEdit:hover {
                background-color: #082044;
                border-color: #4978B8;
            }
            QLineEdit:hover {
                background-color: #082044;
                border-color: #4978B8;
            }
            """
        )
        path_layout.addWidget(self.edit_path, 1)

        btn_browse = self._outline_button(FIF.FOLDER, "Browse", width=112)
        btn_browse.clicked.connect(self.choose_output_path)
        path_layout.addWidget(btn_browse)

        path_outer.addLayout(path_layout)
        main_layout.addWidget(path_card)

        main_layout.addStretch()

        btn_generate = self._outline_button(FIF.SAVE, "Generate XML", height=46)
        btn_generate.setFixedHeight(46)
        btn_generate.clicked.connect(self.generate_xml)
        main_layout.addWidget(btn_generate)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            frame = self.frameGeometry()
            frame.moveCenter(geo.center())
            self.move(frame.topLeft())

    def set_icon(self):
        base_dir = _resource_base_dir()
        ico_path = base_dir / "Images" / "icon.ico"
        png_path = base_dir / "Images" / "icon.png"
        logo_path = ico_path if ico_path.exists() else png_path

        icon = QIcon(str(logo_path))
        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)

    def _default_output_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = _resource_base_dir()
        return str(Path(base_dir) / "login-animation.xml")

    def choose_output_path(self):
        current_path = self.edit_path.text().strip()
        default_path = current_path or str(Path.home() / "Desktop" / "login-animation.xml")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Animation XML",
            default_path,
            "XML files (*.xml);;All files (*.*)"
        )
        if path:
            if not Path(path).suffix:
                path = str(Path(path).with_suffix(".xml"))
            self.edit_path.setText(path)

    def generate_xml(self):
        start = self.spin_start.value()
        end = self.spin_end.value()
        fps = self.spin_fps.value()
        filter_type = self.combo_filter.currentText()

        if start >= end:
            InfoBar.warning(
                title="Invalid range",
                content="Start frame must be less than end frame.",
                parent=self,
                duration=3500,
                position=InfoBarPosition.TOP_RIGHT,
            )
            return

        output_path = self.edit_path.text().strip() or self._default_output_path()
        if not self.edit_path.text().strip():
            self.edit_path.setText(output_path)

        # Calculate duration in milliseconds
        duration_ms = round(1000 / fps)

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<themes>\n')

                # Individual image definitions
                for i in range(start, end + 1):
                    f.write(f'    <images file="anim/Frame{i:04d}.jpg" filter="{filter_type}">\n')
                    f.write(f'        <area name="bg-f{i:05d}" xywh="*"/>\n')
                    f.write('    </images>\n')

                f.write('\n    <images>\n')
                f.write('        <animation name="login-background-animation" timeSource="enabled">\n')

                # Frames
                for i in range(start, end + 1):
                    f.write(f'            <frame ref="bg-f{i:05d}" duration="{duration_ms}"/>\n')

                f.write('        </animation>\n')
                f.write('    </images>\n\n')

                # Themes that use the animation
                f.write('    <theme name="logingui" ref="logingui">\n')
                f.write('        <param name="background"><image>login-background-animation</image></param>\n')
                f.write('    </theme>\n')
                f.write('    <theme name="characterselectgui" ref="characterselectgui">\n')
                f.write('        <param name="background"><image>login-background-animation</image></param>\n')
                f.write('    </theme>\n')

                f.write('</themes>\n')

            self._blue_info("XML generated", str(output_file), duration=5000)

        except Exception as e:
            InfoBar.error(
                title="Failed to write file",
                content=str(e),
                parent=self,
                duration=5000,
                position=InfoBarPosition.TOP_RIGHT,
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnimationGeneratorWindow()
    window.show()
    sys.exit(app.exec())
