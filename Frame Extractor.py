import sys
import os
import importlib.util
import json
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import shutil
import zipfile
from pathlib import Path
import contextlib
import io
import logging
import time
import warnings
from PIL import Image
import imageio.v3 as imageio
from moviepy import VideoFileClip, ImageSequenceClip
from proglog import ProgressBarLogger
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QFileDialog,
    QHBoxLayout, QSizePolicy, QProgressDialog, QGridLayout,
    QDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl
from PySide6.QtGui import QColor, QIcon, QDesktopServices, QPainter

with contextlib.redirect_stdout(io.StringIO()):
    from qfluentwidgets import (
        BodyLabel, CaptionLabel, ComboBox, FluentIcon as FIF, InfoBar,
        InfoBarPosition, LineEdit, PrimaryPushButton, ProgressBar, PushButton,
        ScrollArea, SimpleCardWidget, StrongBodyLabel,
        Theme, setTheme, setThemeColor
    )
    from qfluentwidgets.components.widgets.combo_box import ComboBoxMenu

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
warnings.filterwarnings(
    "ignore",
    message=r"In file .* bytes wanted but 0 bytes read at frame index .* Using the last valid frame instead\.",
    category=UserWarning,
    module=r"moviepy\.video\.io\.ffmpeg_reader",
)


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


class ThemedComboBox(ComboBox):
    def _createComboMenu(self):
        menu = ComboBoxMenu(self)
        menu.view.setStyleSheet(COMBO_DROPDOWN_STYLE)
        return menu


APP_VERSION = "2.1.1"
_GITHUB_OWNER = "Ryukotsuki"
_GITHUB_REPO = "Frame-Extractor"
_GITHUB_PROJECT_PAGE = f"https://github.com/{_GITHUB_OWNER}/{_GITHUB_REPO}"
_GITHUB_RELEASES_PAGE = f"https://github.com/Ryukotsuki/Frame-Extractor/releases"
_GITHUB_RELEASES_API_LATEST = f"https://api.github.com/repos/Ryukotsuki/Frame-Extractor/releases/latest"
ABOUT_DEPENDENCIES = (
    ("PySide6", "Qt desktop UI"),
    ("PySide6-Fluent-Widgets", "Fluent controls"),
    ("MoviePy", "video editing"),
    ("imageio", "frame writing"),
    ("imageio-ffmpeg", "FFmpeg runtime"),
    ("Pillow", "image and GIF tools"),
    ("proglog", "encode progress"),
    ("PyInstaller", "Windows packaging"),
)
FRAME_FILE_PATTERN = re.compile(r"^frame(\d+)$", re.IGNORECASE)
SUPPORTED_FRAME_SUFFIXES = {".jpg", ".jpeg", ".png"}


def _resource_base_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _numbered_frame_files(frames_dir) -> list[str]:
    files = []
    for entry in Path(frames_dir).iterdir():
        if not entry.is_file() or entry.suffix.lower() not in SUPPORTED_FRAME_SUFFIXES:
            continue

        match = FRAME_FILE_PATTERN.match(entry.stem)
        if match is None:
            continue

        files.append((int(match.group(1)), str(entry)))

    return [path for _, path in sorted(files, key=lambda item: (item[0], item[1].lower()))]


def _parse_version(version_str: str):
    if not version_str:
        return (0, 0, 0)
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version_str)
    if not m:
        return (0, 0, 0)
    parts = [int(p) if p is not None else 0 for p in m.groups()]
    return tuple(parts)


class UpdateCheckThread(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            req = urllib.request.Request(
                _GITHUB_RELEASES_API_LATEST,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "FrameExtractor",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self.finished.emit(data)
        except urllib.error.HTTPError as e:
            self.error.emit(f"Update check failed: HTTP {e.code}")
        except Exception as e:
            self.error.emit(f"Update check failed: {str(e)}")


class UpdateDownloadThread(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, url: str, output_path: str):
        super().__init__()
        self.url = url
        self.output_path = output_path

    def run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={
                    "User-Agent": "FrameExtractor",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = resp.headers.get("Content-Length")
                total_bytes = int(total) if total and total.isdigit() else None
                downloaded = 0
                with open(self.output_path, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_bytes:
                            percent = int((downloaded / total_bytes) * 100)
                            self.progress.emit(max(0, min(100, percent)))
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(f"Download failed: {str(e)}")

class ExtractionThread(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, video_path, output_path, resolution, format, extract_fps=None, total_frames=None):
        super().__init__()
        self.video_path = str(video_path)
        self.output_path = Path(output_path)
        self.resolution = resolution
        self.format = str(format).lower()
        self.extract_fps = extract_fps
        self.total_frames = total_frames

    def run(self):
        clip = None
        try:
            clip = VideoFileClip(self.video_path)
            if clip.duration is None or clip.duration <= 0:
                self.error.emit("Could not open video or GIF file")
                return

            orig_fps = clip.fps if clip.fps else 30
            if self.total_frames:
                fps = self.total_frames / clip.duration if clip.duration > 0 else orig_fps
            else:
                fps = self.extract_fps if self.extract_fps else orig_fps

            total_frames = max(1, int(round(clip.duration * fps)))

            output_dir = self.output_path / "frames"
            output_dir.mkdir(parents=True, exist_ok=True)

            if self.resolution:
                if hasattr(clip, "resized"):
                    clip = clip.resized(new_size=self.resolution)
                else:
                    try:
                        clip = clip.resize(newsize=self.resolution)
                    except TypeError:
                        clip = clip.resize(new_size=self.resolution)

            count = 1
            for frame in clip.iter_frames(fps=fps, dtype="uint8"):
                frame_path = output_dir / f"Frame{count:04d}.{self.format}"
                imageio.imwrite(frame_path, frame)
                count += 1
                self.progress.emit(int(((count - 1) / total_frames) * 100))

            self.finished.emit(f"Extracted {count - 1} frames to {output_dir} at effective {fps:.2f} FPS")
        except Exception as e:
            self.error.emit(f"Failed to extract frames: {str(e)}")
        finally:
            if clip is not None:
                clip.close()


class RecombinationThread(QThread):
    progress = Signal(int)
    progress_text = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, frames_dir, output_path, format, fps=30, duration=None):
        super().__init__()
        self.frames_dir = Path(frames_dir)
        self.output_path = Path(output_path)
        self.format = str(format).lower()
        try:
            self.fps = float(fps)
        except (TypeError, ValueError):
            self.fps = 30.0
        if self.fps <= 0:
            self.fps = 30.0

        try:
            self.duration = float(duration) if duration is not None else None
        except (TypeError, ValueError):
            self.duration = None
        if self.duration is not None and self.duration <= 0:
            self.duration = None

    class _MoviePyLogger(ProgressBarLogger):
        def __init__(self, progress_signal, text_signal):
            super().__init__()
            self._progress_signal = progress_signal
            self._text_signal = text_signal
            self._last_percent = -1

        def bars_callback(self, bar, attr, value, old_value=None):
            bar_state = self.bars.get(bar, {})
            total = bar_state.get("total")
            if total in (None, 0):
                return

            index = value if attr == "index" else bar_state.get("index", 0)
            if index is None:
                return

            percent = int((float(index) / float(total)) * 100)
            if percent != self._last_percent:
                self._last_percent = percent
                self._progress_signal.emit(max(0, min(99, percent)))
                self._text_signal.emit(f"Encoding video... {percent}%")

    def run(self):
        try:
            frame_files = _numbered_frame_files(self.frames_dir)

            if not frame_files:
                self.error.emit(f"No numbered frames found in {self.frames_dir}. Expected files like Frame0001.png/jpg")
                return

            total_frames = len(frame_files)
            if self.duration and self.duration > 0:
                self.fps = total_frames / self.duration

            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            if self.format == "mp4":
                self.progress.emit(0)
                self.progress_text.emit("Encoding video...")
                clip = ImageSequenceClip(frame_files, fps=self.fps)
                clip.write_videofile(str(self.output_path), codec="libx264", audio=False,
                                     logger=self._MoviePyLogger(self.progress, self.progress_text),
                                     ffmpeg_params=["-preset", "fast"])
                clip.close()
                self.progress.emit(100)
                self.finished.emit(f"Recombined {total_frames} frames into MP4: {self.output_path}")

            elif self.format == "gif":
                images = []
                try:
                    with Image.open(frame_files[0]) as base_image:
                        base_quant = base_image.convert("RGB").quantize(colors=256, method=2, kmeans=5)
                    palette = base_quant.getpalette()
                    palette_img = Image.new("P", (1, 1))
                    palette_img.putpalette(palette)

                    for i, frame_file in enumerate(frame_files):
                        with Image.open(frame_file) as source_image:
                            quant_img = source_image.convert("RGB").quantize(colors=256, palette=palette_img, dither=0)
                        images.append(quant_img)
                        self.progress.emit(int((i + 1) / total_frames * 99))
                        self.progress_text.emit(f"Processing frame {i + 1}/{total_frames}")

                    self.progress.emit(99)
                    self.progress_text.emit("Finalizing GIF...")
                    images[0].save(
                        str(self.output_path),
                        save_all=True,
                        append_images=images[1:],
                        duration=max(1, int(round(1000 / self.fps))),
                        loop=0,
                        optimize=True
                    )
                    self.progress.emit(100)
                    time.sleep(0.5)
                    self.finished.emit(f"Recombined {total_frames} frames into GIF: {self.output_path}")
                finally:
                    for image in images:
                        image.close()

        except Exception as e:
            logging.error(f"Recombination error: {str(e)}")
            self.error.emit(f"Failed to recombine: {str(e)}")


class VideoFrameExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frame Extractor")
        self.set_icon()
        self.setMinimumSize(1000, 875)

        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            max_h = int(avail.height() * 0.9)
            self.resize(min(1060, avail.width()), min(875, max_h))
            frame = self.frameGeometry()
            frame.moveCenter(avail.center())
            self.move(frame.topLeft())
        else:
            self.resize(1060, 875)

        # State
        self.video_path = None
        self.output_dir = None
        self.frames_dir = None
        self.extraction_thread = None
        self.recombination_thread = None
        self.resolution = None
        self.extract_fps = None
        self.total_frames = None
        self._animation_window = None

        self.apply_theme()
        self.setup_ui()

        QTimer.singleShot(700, lambda: self.check_for_updates(startup=True))

    def apply_theme(self):
        app = QApplication.instance()
        if app is None:
            return

        setTheme(Theme.DARK)
        setThemeColor(QColor("#5B8CFF"))
        app.setStyleSheet("""
        QMainWindow {
            background-color: #070A12;
        }
        QWidget#page {
            background-color: #070A12;
        }
        QWidget#heroPanel {
            background-color: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #132546,
                stop:0.48 #0D1629,
                stop:1 #101824
            );
            border: 1px solid #294B7A;
            border-radius: 16px;
        }
        SimpleCardWidget#surfaceCard {
            background-color: #071426;
            border: 1px solid #23466F;
            border-radius: 14px;
        }
        #statTile {
            background-color: #061225;
            border: 1px solid #254A76;
            border-radius: 10px;
        }
        QWidget#statusStrip {
            background-color: #071426;
            border: 1px solid #254A76;
            border-radius: 10px;
        }
        QWidget#statusPill {
            background-color: #061225;
            border: 1px solid #254A76;
            border-radius: 9px;
        }
        QWidget#separator {
            background-color: #254A76;
            max-height: 1px;
        }
        QLabel {
            color: #EEF5FF;
        }
        QLabel#mutedLabel,
        QLabel#fieldLabel,
        QLabel#statTitle,
        QLabel#pillTitle {
            color: #8FA2BD;
        }
        QLabel#statValue,
        QLabel#pillValue {
            color: #F4F8FF;
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
            color: #DDEAFF;
            border-color: #356EAE;
            background-color: #071B36;
        }
        PushButton,
        QPushButton,
        ComboBox,
        QComboBox,
        LineEdit,
        QLineEdit,
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
        QSpinBox:hover,
        QAbstractSpinBox:hover {
            background-color: #082044;
            border-color: #4978B8;
        }
        PushButton:pressed,
        QPushButton:pressed,
        ComboBox:pressed,
        QComboBox:pressed {
            background-color: #041022;
            border-color: #5B8CFF;
        }
        PrimaryPushButton {
            background-color: #5B8CFF;
            border: 1px solid #78A3FF;
            border-radius: 9px;
            color: #061021;
            padding: 8px 14px;
        }
        PrimaryPushButton:hover {
            background-color: #74A0FF;
            border-color: #9AB9FF;
        }
        PrimaryPushButton:pressed {
            background-color: #4677E8;
            border-color: #6D94F4;
        }
        PushButton:disabled,
        QPushButton:disabled,
        PrimaryPushButton:disabled,
        QLineEdit:disabled,
        LineEdit:disabled,
        QComboBox:disabled,
        ComboBox:disabled {
            background-color: #071120;
            border-color: #1E4069;
            color: #64728A;
        }
        ProgressBar {
            min-height: 8px;
            max-height: 8px;
        }
        QScrollArea {
            background: transparent;
            border: none;
        }
        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 3px;
        }
        QScrollBar::handle:vertical {
            background: #263C5E;
            border-radius: 5px;
            min-height: 32px;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """
        )

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

    def open_login_animation_generator(self):
        """Open the Login Animation XML Generator window (styled like this app)."""
        gui_path = _resource_base_dir() / "Source" / "Login Animation.py"
        if not gui_path.is_file():
            InfoBar.error(
                title="File not found",
                content=f"Login Animation GUI not found: {gui_path}",
                parent=self,
                duration=5000,
                position=InfoBarPosition.TOP_RIGHT,
            )
            return
        try:
            spec = importlib.util.spec_from_file_location("login_animation_gui", gui_path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Could not load Login Animation GUI: {gui_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._animation_window = module.AnimationGeneratorWindow(use_global_theme=False)
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                frame = self._animation_window.frameGeometry()
                frame.moveCenter(geo.center())
                self._animation_window.move(frame.topLeft())
            self._animation_window.show()
            self._animation_window.raise_()
            self._animation_window.activateWindow()
        except Exception as e:
            InfoBar.error(
                title="Could not open tool",
                content=str(e),
                parent=self,
                duration=5000,
                position=InfoBarPosition.TOP_RIGHT,
            )

    def _button(self, icon, text, primary=False):
        button = PrimaryPushButton(icon, text) if primary else PushButton(icon, text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(38)
        button.setStyleSheet(
            """
            PushButton {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #F2F7FF;
                padding: 7px 12px;
            }
            QPushButton {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #F2F7FF;
                padding: 7px 12px;
            }
            PushButton[hasIcon=true] {
                padding-left: 34px;
            }
            QPushButton[hasIcon=true] {
                padding-left: 34px;
            }
            PushButton:hover {
                background-color: #082044;
                border-color: #4978B8;
            }
            QPushButton:hover {
                background-color: #082044;
                border-color: #4978B8;
            }
            PushButton:pressed {
                background-color: #041022;
                border-color: #5B8CFF;
            }
            QPushButton:pressed {
                background-color: #041022;
                border-color: #5B8CFF;
            }
            PrimaryPushButton {
                background-color: #5B8CFF;
                border: 1px solid #78A3FF;
                border-radius: 9px;
                color: #FFFFFF;
                padding: 8px 14px;
            }
            PrimaryPushButton[hasIcon=true] {
                padding-left: 36px;
            }
            PrimaryPushButton:hover {
                background-color: #74A0FF;
                border-color: #9AB9FF;
            }
            PrimaryPushButton:pressed {
                background-color: #4677E8;
                border-color: #6D94F4;
            }
            PushButton:disabled,
            QPushButton:disabled,
            PrimaryPushButton:disabled {
                background-color: #071120;
                border-color: #1E4069;
                color: #64728A;
            }
            """
        )
        return button

    def _header_button(self, icon, text, width=138):
        button = PushButton(icon, text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedHeight(58)
        button.setMinimumWidth(width)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setStyleSheet(
            """
            PushButton,
            QPushButton {
                background-color: #061225;
                border: 1px solid #254A76;
                border-radius: 10px;
                color: #F4F8FF;
                padding: 0px 14px;
                font-weight: 600;
            }
            PushButton[hasIcon=true],
            QPushButton[hasIcon=true] {
                padding-left: 38px;
            }
            PushButton:hover,
            QPushButton:hover {
                background-color: #082044;
                border-color: #4978B8;
                color: #FFFFFF;
            }
            PushButton:pressed,
            QPushButton:pressed {
                background-color: #071B36;
                border-color: #5B8CFF;
            }
            PushButton:disabled,
            QPushButton:disabled {
                background-color: #071120;
                border-color: #1E4069;
                color: #64728A;
            }
            """
        )
        return button

    def _action_button(self, icon, text):
        button = PushButton(icon, text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(46)
        button.setStyleSheet(
            """
            PushButton,
            QPushButton {
                background-color: #082044;
                border: 1px solid #3A72B8;
                border-radius: 10px;
                color: #EAF3FF;
                padding: 9px 14px;
                font-weight: 600;
            }
            PushButton[hasIcon=true],
            QPushButton[hasIcon=true] {
                padding-left: 38px;
            }
            PushButton:hover,
            QPushButton:hover {
                background-color: #0B2A57;
                border-color: #5B8CFF;
                color: #FFFFFF;
            }
            PushButton:pressed,
            QPushButton:pressed {
                background-color: #061A38;
                border-color: #79A6FF;
            }
            PushButton:disabled,
            QPushButton:disabled {
                background-color: #061225;
                border-color: #254A76;
                color: #7890AD;
            }
            """
        )
        return button

    def _card(self, title):
        card = BlueCardWidget()
        card.setObjectName("surfaceCard")
        card.setBackgroundColor(QColor("#071426"))
        card.setBorderRadius(14)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(16)

        heading = StrongBodyLabel(title)
        layout.addWidget(heading)
        return card, layout

    def _field(self, text, widget):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = CaptionLabel(text)
        label.setObjectName("fieldLabel")
        widget.setMinimumHeight(40)
        widget.setFixedHeight(40)
        widget.setStyleSheet(
            widget.styleSheet() + """
            LineEdit,
            QLineEdit,
            ComboBox {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #EAF3FF;
                placeholder-text-color: #BFD4F2;
                selection-background-color: #2F5C93;
                selection-color: #FFFFFF;
                padding: 7px 12px;
            }
            QComboBox {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #EAF3FF;
                padding: 7px 12px;
            }
            LineEdit:hover,
            QLineEdit:hover,
            ComboBox:hover {
                background-color: #082044;
                border-color: #4978B8;
            }
            QComboBox:hover {
                background-color: #082044;
                border-color: #4978B8;
            }
            LineEdit:focus {
                background-color: #061225;
                border-color: #5B8CFF;
                color: #FFFFFF;
            }
            LineEdit:focus[transparent=true],
            LineEdit[transparent=false]:focus {
                background-color: #061225;
                border: 1px solid #5B8CFF;
                border-bottom: 1px solid #5B8CFF;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                background-color: #061225;
                border-color: #5B8CFF;
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
            LineEdit:disabled,
            QLineEdit:disabled,
            ComboBox:disabled {
                background-color: #071120;
                border-color: #1E4069;
                color: #64728A;
            }
            QComboBox:disabled {
                background-color: #071120;
                border-color: #1E4069;
                color: #64728A;
            }
            """
        )
        layout.addWidget(label)
        layout.addWidget(widget)
        container.setMinimumHeight(66)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return container

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

    def _confirm_dialog(self, title, heading, content, accept_text="Yes", reject_text="No"):
        dialog = QDialog(self)
        dialog.setObjectName("confirmDialog")
        dialog.setWindowTitle(title)
        dialog.setWindowIcon(self.windowIcon())
        dialog.setModal(True)
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet(
            """
            QDialog#confirmDialog {
                background-color: #070A12;
            }
            QLabel#confirmTitle {
                color: #F4F8FF;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#confirmBody {
                color: #DCE8F9;
                line-height: 1.35em;
            }
            """
        )

        root = QVBoxLayout(dialog)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        panel = BlueCardWidget()
        panel.setBackgroundColor(QColor("#071426"))
        panel.setBorderRadius(14)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 18, 20, 20)
        panel_layout.setSpacing(12)

        title_label = QLabel(heading)
        title_label.setObjectName("confirmTitle")
        title_label.setWordWrap(True)
        panel_layout.addWidget(title_label)

        body = BodyLabel(content)
        body.setObjectName("confirmBody")
        body.setWordWrap(True)
        panel_layout.addWidget(body)
        root.addWidget(panel)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        if reject_text:
            cancel_btn = self._button(FIF.CLOSE, reject_text)
            cancel_btn.setMinimumHeight(40)
            cancel_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            cancel_btn.clicked.connect(dialog.reject)
            actions.addWidget(cancel_btn, 1)

        accept_btn = self._button(FIF.ACCEPT, accept_text)
        accept_btn.setMinimumHeight(40)
        accept_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        accept_btn.clicked.connect(dialog.accept)
        actions.addWidget(accept_btn, 1)

        root.addLayout(actions)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def _build_about_dialog(self):
        dialog = QDialog(self)
        dialog.setObjectName("aboutDialog")
        dialog.setWindowTitle("About")
        dialog.setWindowIcon(self.windowIcon())
        dialog.setModal(True)
        dialog.setMinimumWidth(560)
        dialog.setStyleSheet(
            """
            QDialog#aboutDialog {
                background-color: #070A12;
            }
            QLabel#aboutSummary {
                color: #DCE8F9;
                line-height: 1.35em;
            }
            QLabel#aboutSection {
                color: #F4F8FF;
                font-weight: 700;
            }
            QLabel#aboutMeta {
                color: #8FA2BD;
            }
            """
        )

        root = QVBoxLayout(dialog)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(16)

        panel = BlueCardWidget()
        panel.setBackgroundColor(QColor("#071426"))
        panel.setBorderRadius(14)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 20, 22, 22)
        panel_layout.setSpacing(16)

        summary = BodyLabel(
            "A focused desktop tool for extracting frames from videos or GIFs, "
            "recombining frame folders, and generating login-animation XML."
        )
        summary.setObjectName("aboutSummary")
        summary.setWordWrap(True)
        panel_layout.addWidget(summary)

        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(12)
        details_grid.setVerticalSpacing(12)
        version_tile, _ = self._stat_tile("Version", APP_VERSION)
        details_grid.addWidget(version_tile, 0, 0, 1, 2)
        panel_layout.addLayout(details_grid)

        dependencies_heading = StrongBodyLabel("Dependencies")
        dependencies_heading.setObjectName("aboutSection")
        panel_layout.addWidget(dependencies_heading)

        dependencies_grid = QGridLayout()
        dependencies_grid.setHorizontalSpacing(12)
        dependencies_grid.setVerticalSpacing(12)
        for index, (name, purpose) in enumerate(ABOUT_DEPENDENCIES):
            tile, _ = self._stat_tile(name, purpose)
            dependencies_grid.addWidget(tile, index // 2, index % 2)
        panel_layout.addLayout(dependencies_grid)

        note = CaptionLabel("Built for local media workflows with no cloud upload required.")
        note.setObjectName("aboutMeta")
        note.setWordWrap(True)
        panel_layout.addWidget(note)

        root.addWidget(panel)

        close_btn = self._button(FIF.CLOSE, "Close")
        close_btn.setMinimumHeight(40)
        close_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        close_btn.clicked.connect(dialog.accept)

        github_btn = self._button(FIF.GITHUB, "GitHub")
        github_btn.setMinimumHeight(40)
        github_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        github_btn.clicked.connect(
            lambda checked=False: QDesktopServices.openUrl(QUrl(_GITHUB_PROJECT_PAGE))
        )

        actions = QHBoxLayout()
        actions.setSpacing(16)
        actions.addWidget(close_btn, 1)
        actions.addWidget(github_btn, 1)
        root.addLayout(actions)

        return dialog

    def open_about_dialog(self):
        self._build_about_dialog().exec()

    def _stat_tile(self, title, value="--"):
        tile = QWidget()
        tile.setObjectName("statTile")
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(12, 10, 12, 10)
        tile_layout.setSpacing(3)
        tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        title_label = CaptionLabel(title)
        title_label.setObjectName("statTitle")
        value_label = StrongBodyLabel(value)
        value_label.setObjectName("statValue")
        value_label.setWordWrap(True)

        tile_layout.addWidget(title_label)
        tile_layout.addWidget(value_label)
        return tile, value_label

    def _status_pill(self, title, value="Waiting"):
        pill = QWidget()
        pill.setObjectName("statusPill")
        pill_layout = QVBoxLayout(pill)
        pill_layout.setContentsMargins(12, 9, 12, 9)
        pill_layout.setSpacing(3)
        pill.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        title_label = CaptionLabel(title)
        title_label.setObjectName("pillTitle")
        value_label = BodyLabel(value)
        value_label.setObjectName("pillValue")
        value_label.setWordWrap(True)

        pill_layout.addWidget(title_label)
        pill_layout.addWidget(value_label)
        return pill, value_label

    def _separator(self):
        line = QWidget()
        line.setObjectName("separator")
        line.setFixedHeight(1)
        return line

    def _compact_path(self, path, max_chars=46):
        text = str(path)
        if len(text) <= max_chars:
            return text

        path_obj = Path(text)
        tail = f"{path_obj.parent.name}\\{path_obj.name}" if path_obj.parent.name else path_obj.name
        if len(tail) + 4 <= max_chars:
            return f"...\\{tail}"

        return f"...{text[-max_chars + 3:]}"

    def setup_ui(self):
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        page = QWidget()
        page.setObjectName("page")
        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(page)
        layout.setSpacing(22)
        layout.setContentsMargins(28, 28, 28, 28)

        hero = QWidget()
        hero.setObjectName("heroPanel")
        hero.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(16)

        status_strip = QWidget()
        status_strip.setObjectName("statusStrip")
        status_strip.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        status_layout = QHBoxLayout(status_strip)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(10)

        source_tile, self.header_source_status = self._stat_tile("Source", "No media")
        frames_tile, self.header_frames_status = self._stat_tile("Frames", "--")
        output_tile, self.header_output_status = self._stat_tile("Output", "Not set")
        status_layout.addWidget(source_tile, 1)
        status_layout.addWidget(frames_tile, 1)
        status_layout.addWidget(output_tile, 1)
        hero_layout.addWidget(status_strip, 3)

        action_strip = QWidget()
        action_strip.setObjectName("statusStrip")
        action_strip.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        action_layout = QHBoxLayout(action_strip)
        action_layout.setContentsMargins(12, 10, 12, 10)
        action_layout.setSpacing(10)

        login_anim_btn = self._header_button(FIF.CODE, "Login XML", 124)
        login_anim_btn.clicked.connect(self.open_login_animation_generator)
        action_layout.addWidget(login_anim_btn, 1)

        update_btn = self._header_button(FIF.UPDATE, "Check Updates", 146)
        update_btn.clicked.connect(lambda: self.check_for_updates(startup=False))
        action_layout.addWidget(update_btn, 1)

        about_btn = self._header_button(FIF.INFO, "About", 112)
        about_btn.clicked.connect(self.open_about_dialog)
        action_layout.addWidget(about_btn, 1)

        hero_layout.addWidget(action_strip, 2)
        layout.addWidget(hero, 0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(22)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)

        extract_card, extract_layout = self._card("Extract Frames")
        select_video_btn = self._button(FIF.VIDEO, "Select Video or GIF")
        select_video_btn.clicked.connect(self.select_video)
        extract_layout.addWidget(select_video_btn)

        self.info_label = BodyLabel("No file selected")
        self.info_label.setObjectName("infoPanel")
        self.info_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.info_label.setMinimumHeight(76)
        self.info_label.setWordWrap(True)
        extract_layout.addWidget(self.info_label)

        metrics_grid = QGridLayout()
        metrics_grid.setHorizontalSpacing(12)
        metrics_grid.setVerticalSpacing(12)
        fps_tile, self.metric_fps = self._stat_tile("Original FPS")
        frames_tile, self.metric_frames = self._stat_tile("Approx Frames")
        resolution_tile, self.metric_resolution = self._stat_tile("Resolution")
        duration_tile, self.metric_duration = self._stat_tile("Duration")
        metrics_grid.addWidget(fps_tile, 0, 0)
        metrics_grid.addWidget(frames_tile, 0, 1)
        metrics_grid.addWidget(resolution_tile, 0, 2)
        metrics_grid.addWidget(duration_tile, 0, 3)
        extract_layout.addLayout(metrics_grid)

        settings_grid = QGridLayout()
        settings_grid.setHorizontalSpacing(14)
        settings_grid.setVerticalSpacing(16)
        settings_grid.setColumnStretch(0, 1)
        settings_grid.setColumnStretch(1, 1)

        self.res_combo = ThemedComboBox()
        self.res_combo.addItems(["Original", "1920x1080", "2560x1440", "3840x2160", "Custom"])
        self.res_combo.currentTextChanged.connect(self.update_resolution)
        settings_grid.addWidget(self._field("Resolution", self.res_combo), 0, 0)

        self.custom_res_input = LineEdit()
        self.custom_res_input.setPlaceholderText("1280x720")
        self.custom_res_input.textChanged.connect(self.update_custom_resolution)
        self.custom_res_field = self._field("Custom size", self.custom_res_input)
        self.custom_res_field.setVisible(False)
        settings_grid.addWidget(self.custom_res_field, 2, 0, 1, 2)

        self.format_combo = ThemedComboBox()
        self.format_combo.addItems(["jpg", "png"])
        settings_grid.addWidget(self._field("Frame format", self.format_combo), 1, 0)

        self.extract_fps_input = LineEdit()
        self.extract_fps_input.setPlaceholderText("Original")
        self.extract_fps_input.textChanged.connect(self.update_extract_fps)
        settings_grid.addWidget(self._field("Extract FPS", self.extract_fps_input), 0, 1)

        self.total_frames_input = LineEdit()
        self.total_frames_input.setPlaceholderText("All frames")
        self.total_frames_input.textChanged.connect(self.update_total_frames)
        settings_grid.addWidget(self._field("Total frames", self.total_frames_input), 1, 1)
        extract_layout.addLayout(settings_grid)

        output_row = QHBoxLayout()
        output_row.setSpacing(12)
        select_output_btn = self._button(FIF.FOLDER, "Output Folder")
        select_output_btn.clicked.connect(self.select_output_dir)
        output_row.addWidget(select_output_btn)

        self.output_label = QLabel("No output directory selected")
        self.output_label.setObjectName("pathLabel")
        self.output_label.setWordWrap(True)
        self.output_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        output_row.addWidget(self.output_label, 1)
        extract_layout.addLayout(output_row)

        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        extract_layout.addWidget(self.progress_bar)

        self.progress_label = BodyLabel("Progress: Idle")
        self.progress_label.setObjectName("progressLabel")
        self.progress_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        extract_layout.addWidget(self.progress_label)

        self.extract_btn = self._action_button(FIF.IMAGE_EXPORT, "Extract Frames")
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self.extract_frames)
        extract_layout.addWidget(self.extract_btn)
        extract_layout.addStretch(1)

        recombine_card, recombine_layout = self._card("Recombine")
        recombine_card.setMinimumWidth(320)
        recombine_grid = QGridLayout()
        recombine_grid.setHorizontalSpacing(14)
        recombine_grid.setVerticalSpacing(16)

        self.recom_combo = ThemedComboBox()
        self.recom_combo.addItems(["None", "gif", "mp4"])
        self.recom_combo.currentTextChanged.connect(self.check_recom_button)
        recombine_grid.addWidget(self._field("Recombine to", self.recom_combo), 0, 0)

        self.fps_input = LineEdit()
        self.fps_input.setText("30")
        recombine_grid.addWidget(self._field("FPS", self.fps_input), 0, 1)

        self.duration_input = LineEdit()
        self.duration_input.setPlaceholderText("optional")
        recombine_grid.addWidget(self._field("Duration (s)", self.duration_input), 1, 0, 1, 2)
        recombine_layout.addLayout(recombine_grid)

        self.select_frames_btn = self._button(FIF.FOLDER_ADD, "Frames Folder")
        self.select_frames_btn.clicked.connect(self.select_frames_dir)
        recombine_layout.addWidget(self.select_frames_btn)

        self.frames_dir_label = QLabel("No frames directory selected")
        self.frames_dir_label.setObjectName("pathLabel")
        self.frames_dir_label.setWordWrap(True)
        self.frames_dir_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        recombine_layout.addWidget(self.frames_dir_label)

        self.recom_btn = self._action_button(FIF.MOVIE, "Recombine Frames")
        self.recom_btn.setEnabled(False)
        self.recom_btn.clicked.connect(self.recombine_frames)
        recombine_layout.addWidget(self.recom_btn)

        recombine_layout.addWidget(self._separator())

        session_heading = StrongBodyLabel("Session")
        recombine_layout.addWidget(session_heading)

        session_grid = QGridLayout()
        session_grid.setHorizontalSpacing(10)
        session_grid.setVerticalSpacing(10)
        source_pill, self.session_source_status = self._status_pill("Source", "No media")
        output_pill, self.session_output_status = self._status_pill("Output", "Not set")
        frames_pill, self.session_frames_status = self._status_pill("Frames Folder", "Not set")
        export_pill, self.session_export_status = self._status_pill("Export", "Idle")
        session_grid.addWidget(source_pill, 0, 0)
        session_grid.addWidget(output_pill, 0, 1)
        session_grid.addWidget(frames_pill, 1, 0)
        session_grid.addWidget(export_pill, 1, 1)
        recombine_layout.addLayout(session_grid)
        recombine_layout.addStretch()

        grid.addWidget(extract_card, 0, 0)
        grid.addWidget(recombine_card, 0, 1)
        layout.addLayout(grid, 1)

        scroll.setWidget(page)
        self.setCentralWidget(scroll)

    def _select_release_asset(self, release_data: dict):
        assets = release_data.get("assets") or []
        zip_assets = [a for a in assets if str(a.get("name", "")).lower().endswith(".zip")]
        if zip_assets:
            zip_assets.sort(key=lambda a: int(a.get("size") or 0), reverse=True)
            return zip_assets[0]
        exe_assets = [a for a in assets if str(a.get("name", "")).lower().endswith(".exe")]
        if exe_assets:
            exe_assets.sort(key=lambda a: int(a.get("size") or 0), reverse=True)
            return exe_assets[0]
        return None

    def check_for_updates(self, startup: bool = False):
        if hasattr(self, "_update_check_thread") and self._update_check_thread and self._update_check_thread.isRunning():
            return

        self._update_check_startup = bool(startup)
        self._update_check_thread = UpdateCheckThread()
        self._update_check_thread.finished.connect(self._on_update_check_finished)
        self._update_check_thread.error.connect(self._on_update_check_error)
        self._update_check_thread.start()

    def _on_update_check_error(self, message: str):
        if getattr(self, "_update_check_startup", False):
            logging.warning(message)
            return
        InfoBar.warning(
            title="Update check failed",
            content=message,
            parent=self,
            duration=4000,
            position=InfoBarPosition.TOP_RIGHT,
        )

    def _on_update_check_finished(self, data: dict):
        latest_tag = (data.get("tag_name") or data.get("name") or "").strip()
        current = _parse_version(APP_VERSION)
        latest = _parse_version(latest_tag)

        if latest <= current:
            if not getattr(self, "_update_check_startup", False):
                self._blue_info("Up to date", "You are already on the latest version.", duration=3000)
            return

        asset = self._select_release_asset(data)
        if asset is None:
            if self._confirm_dialog(
                "Update Available",
                f"Update available: {latest_tag}",
                "No downloadable installer was found for this release. Open the releases page?",
                accept_text="Open Releases",
                reject_text="Not Now",
            ):
                QDesktopServices.openUrl(QUrl(_GITHUB_RELEASES_PAGE))
            return

        asset_name = asset.get("name") or ""
        if not self._confirm_dialog(
            "Update Available",
            f"Update available: {latest_tag}",
            f"Download: {asset_name}\n\nDownload and install this update?",
            accept_text="Update",
            reject_text="Not Now",
        ):
            return

        self._start_update_download(asset, latest_tag)

    def _start_update_download(self, asset: dict, latest_tag: str):
        browser_url = asset.get("browser_download_url")
        asset_name = asset.get("name") or "FrameExtractor.update"
        if not browser_url:
            self._confirm_dialog(
                "Update",
                "Download unavailable",
                "This release asset does not include a downloadable URL.",
                accept_text="Close",
                reject_text=None,
            )
            return

        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", asset_name).strip("._") or "FrameExtractor.update"
        download_path = Path(tempfile.gettempdir()) / f"frame_extractor_update_{os.getpid()}_{safe_name}"
        self._pending_update_asset_name = asset_name
        self._pending_update_latest_tag = latest_tag
        self._update_progress = QProgressDialog("Downloading update...", None, 0, 100, self)
        self._update_progress.setWindowTitle("Update")
        self._update_progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._update_progress.setCancelButton(None)
        self._update_progress.setMinimumWidth(420)
        self._update_progress.setStyleSheet(
            """
            QProgressDialog {
                background-color: #070A12;
                color: #EEF5FF;
            }
            QLabel {
                color: #DCE8F9;
            }
            QProgressBar {
                background-color: #061225;
                border: 1px solid #2E5688;
                border-radius: 8px;
                color: #F4F8FF;
                min-height: 14px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #5B8CFF;
                border-radius: 7px;
            }
            """
        )
        self._update_progress.setValue(0)

        self._update_download_thread = UpdateDownloadThread(browser_url, str(download_path))
        self._update_download_thread.progress.connect(self._update_progress.setValue)
        self._update_download_thread.finished.connect(self._on_update_download_finished)
        self._update_download_thread.error.connect(self._on_update_download_error)
        self._update_download_thread.start()
        self._update_progress.show()

    def _on_update_download_error(self, message: str):
        if hasattr(self, "_update_progress") and self._update_progress:
            self._update_progress.close()
        self._confirm_dialog(
            "Update",
            "Download failed",
            message,
            accept_text="Close",
            reject_text=None,
        )

    def _on_update_download_finished(self, downloaded_path: str):
        if hasattr(self, "_update_progress") and self._update_progress:
            self._update_progress.setValue(100)
            self._update_progress.close()

        downloaded = Path(downloaded_path)
        asset_name = getattr(self, "_pending_update_asset_name", downloaded.name)
        if not getattr(sys, "frozen", False):
            self._confirm_dialog(
                "Update downloaded",
                "Update downloaded",
                f"Saved to:\n{downloaded}\n\nAutomatic installation runs in packaged builds.",
                accept_text="Close",
                reject_text=None,
            )
            return

        if downloaded.suffix.lower() == ".zip" or str(asset_name).lower().endswith(".zip"):
            self._prepare_folder_update(downloaded)
        else:
            self._prepare_exe_update(downloaded)

    def _prepare_exe_update(self, downloaded_path: Path):
        exe_path = Path(sys.executable).resolve()
        exe_dir = exe_path.parent
        old_path = exe_dir / f"{exe_path.stem}.old{exe_path.suffix}"

        bat_contents = "\r\n".join(
            [
                "@echo off",
                "setlocal",
                "set EXE=\"%~1\"",
                "set NEW=\"%~2\"",
                "set OLD=\"%~3\"",
                ":loop",
                "move /Y %EXE% %OLD% >nul 2>&1",
                "if exist %OLD% goto moved",
                "timeout /t 1 /nobreak >nul",
                "goto loop",
                ":moved",
                "move /Y %NEW% %EXE% >nul 2>&1",
                "start \"\" %EXE%",
                "exit",
            ]
        )

        bat_path = Path(tempfile.gettempdir()) / f"frame_extractor_update_{os.getpid()}.bat"
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_contents)

        restart_now = self._confirm_dialog(
            "Update",
            "Update downloaded",
            "Restart now to install the update?",
            accept_text="Restart",
            reject_text="Later",
        )
        if not restart_now:
            return

        subprocess.Popen(
            [
                "cmd",
                "/c",
                "start",
                "",
                str(bat_path),
                str(exe_path),
                str(downloaded_path),
                str(old_path),
            ],
            cwd=str(exe_dir),
            shell=False,
        )
        QApplication.instance().quit()

    def _safe_extract_zip(self, zip_path: Path, extract_root: Path):
        extract_root_resolved = extract_root.resolve()
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                target = (extract_root / member.filename).resolve()
                if target != extract_root_resolved and extract_root_resolved not in target.parents:
                    raise ValueError(f"Unsafe path in update archive: {member.filename}")
            archive.extractall(extract_root)

    def _resolve_update_payload_dir(self, extract_root: Path):
        entries = [
            p for p in extract_root.iterdir()
            if p.name != "__MACOSX" and not p.name.startswith(".")
        ]
        dirs = [p for p in entries if p.is_dir()]
        files = [p for p in entries if p.is_file()]
        if len(dirs) == 1 and not files:
            return dirs[0]
        return extract_root

    def _find_update_executable(self, payload_dir: Path):
        current_name = Path(sys.executable).name.lower()
        exe_files = [p for p in payload_dir.rglob("*.exe") if p.is_file()]
        if not exe_files:
            raise FileNotFoundError("The update archive does not contain an executable.")

        matching = [p for p in exe_files if p.name.lower() == current_name]
        candidates = matching or [p for p in exe_files if "frame" in p.name.lower()] or exe_files
        selected = sorted(candidates, key=lambda p: (len(p.relative_to(payload_dir).parts), str(p)))[0]
        return selected.relative_to(payload_dir)

    def _prepare_folder_update(self, downloaded_path: Path):
        app_dir = Path(sys.executable).resolve().parent
        extract_root = Path(tempfile.mkdtemp(prefix="frame_extractor_update_"))
        try:
            self._safe_extract_zip(downloaded_path, extract_root)
            payload_dir = self._resolve_update_payload_dir(extract_root)
            launch_rel = self._find_update_executable(payload_dir)
        except Exception as e:
            shutil.rmtree(extract_root, ignore_errors=True)
            self._confirm_dialog(
                "Update",
                "Could not prepare update",
                str(e),
                accept_text="Close",
                reject_text=None,
            )
            return

        bat_contents = "\r\n".join(
            [
                "@echo off",
                "setlocal",
                "set \"APP_DIR=%~1\"",
                "set \"PAYLOAD_DIR=%~2\"",
                "set \"LAUNCH_REL=%~3\"",
                "set \"EXTRACT_ROOT=%~4\"",
                "set \"APP_NAME=%~nx1\"",
                "set \"APP_PARENT=%~dp1\"",
                "set \"BACKUP_DIR=%APP_PARENT%%APP_NAME%.old\"",
                "set \"NEW_DIR=%APP_PARENT%%APP_NAME%\"",
                "timeout /t 1 /nobreak >nul",
                "pushd \"%APP_PARENT%\" || exit /b 1",
                "if exist \"%APP_NAME%.old\" rmdir /s /q \"%APP_NAME%.old\"",
                ":rename",
                "ren \"%APP_NAME%\" \"%APP_NAME%.old\" >nul 2>nul",
                "if exist \"%APP_NAME%.old\" goto copy",
                "timeout /t 1 /nobreak >nul",
                "goto rename",
                ":copy",
                "mkdir \"%APP_NAME%\"",
                "robocopy \"%PAYLOAD_DIR%\" \"%APP_NAME%\" /MIR /NFL /NDL /NJH /NJS /NC /NS /NP",
                "set \"ROBO=%ERRORLEVEL%\"",
                "if %ROBO% GEQ 8 goto restore",
                "start \"\" \"%NEW_DIR%\\%LAUNCH_REL%\"",
                "rmdir /s /q \"%BACKUP_DIR%\" >nul 2>nul",
                "rmdir /s /q \"%EXTRACT_ROOT%\" >nul 2>nul",
                "popd",
                "del \"%~f0\"",
                "exit /b 0",
                ":restore",
                "rmdir /s /q \"%NEW_DIR%\" >nul 2>nul",
                "ren \"%APP_NAME%.old\" \"%APP_NAME%\" >nul 2>nul",
                "popd",
                "exit /b 1",
            ]
        )

        bat_path = Path(tempfile.gettempdir()) / f"frame_extractor_folder_update_{os.getpid()}.bat"
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_contents)

        restart_now = self._confirm_dialog(
            "Update",
            "Update downloaded",
            "Restart now to replace the current app folder with the downloaded update?",
            accept_text="Restart",
            reject_text="Later",
        )
        if not restart_now:
            return

        subprocess.Popen(
            [
                "cmd",
                "/c",
                "start",
                "",
                str(bat_path),
                str(app_dir),
                str(payload_dir),
                str(launch_rel),
                str(extract_root),
            ],
            cwd=str(app_dir.parent),
            shell=False,
        )
        QApplication.instance().quit()

    # ─────────────────────────────────────────────────────────────
    # Methods (update_*, select_*, check_*, display_*, extract_*, recombine_*, finished/error handlers)
    # ─────────────────────────────────────────────────────────────

    def update_resolution(self, text):
        if text == "Custom":
            self.custom_res_field.setVisible(True)
            self.resolution = None
        else:
            self.custom_res_field.setVisible(False)
            if text == "Original":
                self.resolution = None
            else:
                try:
                    w, h = map(int, text.split("x"))
                    self.resolution = (w, h)
                except ValueError:
                    self.resolution = None

    def update_custom_resolution(self, text):
        if "x" in text:
            try:
                w, h = map(int, text.replace(" ", "").split("x"))
                if w > 0 and h > 0:
                    self.resolution = (w, h)
                else:
                    self.resolution = None
            except ValueError:
                self.resolution = None
        else:
            self.resolution = None

    def update_extract_fps(self, text):
        try:
            val = text.strip()
            self.extract_fps = float(val) if val else None
            if self.extract_fps is not None and self.extract_fps <= 0:
                self.extract_fps = None
            if self.video_path:
                self.display_video_info()
        except ValueError:
            self.extract_fps = None

    def update_total_frames(self, text):
        try:
            val = text.strip()
            self.total_frames = int(val) if val else None
            if self.total_frames is not None and self.total_frames <= 0:
                self.total_frames = None
            if self.video_path:
                self.display_video_info()
        except ValueError:
            self.total_frames = None

    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video or GIF", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.gif)"
        )
        if path:
            self.video_path = path
            self.display_video_info()
            self.check_extract_button()

    def select_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_dir = Path(path)
            output_text = self._compact_path(self.output_dir, 42)
            session_output_text = self._compact_path(self.output_dir, 28)
            self.output_label.setText(output_text)
            self.header_output_status.setText("Ready")
            self.session_output_status.setText(session_output_text)
            self.check_extract_button()
        else:
            self.output_dir = None
            self.output_label.setText("No output directory selected")
            self.header_output_status.setText("Not set")
            self.session_output_status.setText("Not set")
            self.check_extract_button()

    def select_frames_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Frames Directory")
        if path:
            self.frames_dir = Path(path)
            frames_text = self._compact_path(self.frames_dir, 38)
            session_frames_text = self._compact_path(self.frames_dir, 28)
            self.frames_dir_label.setText(frames_text)
            self.session_frames_status.setText(session_frames_text)
            self.check_recom_button()
        else:
            self.frames_dir = None
            self.frames_dir_label.setText("No frames directory selected")
            self.session_frames_status.setText("Not set")
            self.check_recom_button()

    def check_extract_button(self):
        self.extract_btn.setEnabled(bool(self.video_path and self.output_dir))

    def check_recom_button(self):
        mode = self.recom_combo.currentText()
        ready = bool(self.frames_dir and mode != "None")
        self.recom_btn.setEnabled(ready)
        if ready:
            self.session_export_status.setText(f"{mode.upper()} ready")
        elif mode == "None":
            self.session_export_status.setText("No format")
        else:
            self.session_export_status.setText("Waiting")

    def display_video_info(self):
        clip = None
        try:
            clip = VideoFileClip(self.video_path)
            fps = clip.fps if clip.fps else 0
            duration = clip.duration if clip.duration else 0
            width, height = clip.size

            if self.total_frames:
                est_frames = self.total_frames
                est_fps = self.total_frames / duration if duration > 0 else fps
                extract_text = f" (target {est_frames} frames ~{est_fps:.2f} fps)"
            elif self.extract_fps:
                est_frames = int(round(duration * self.extract_fps))
                extract_text = f" (at {self.extract_fps} fps)"
            else:
                est_frames = int(round(duration * fps)) if fps > 0 else 0
                extract_text = ""

            file_name = os.path.basename(self.video_path)
            source_path = self._compact_path(self.video_path, 70)
            info = f"<b>{file_name}</b><br>{source_path}{extract_text}"
            self.info_label.setText(info)
            self.header_source_status.setText(file_name)
            self.header_frames_status.setText(str(est_frames))
            self.session_source_status.setText(file_name)
            self.metric_fps.setText(f"{fps:.2f}")
            self.metric_frames.setText(str(est_frames))
            self.metric_resolution.setText(f"{width}x{height}")
            self.metric_duration.setText(f"{duration:.2f} s")
        except Exception as e:
            self.info_label.setText(f"Cannot read file info: {str(e)}")
            self.header_source_status.setText("Unreadable")
            self.header_frames_status.setText("--")
            self.session_source_status.setText("Unreadable")
            self.metric_fps.setText("--")
            self.metric_frames.setText("--")
            self.metric_resolution.setText("--")
            self.metric_duration.setText("--")
        finally:
            if clip is not None:
                clip.close()

    def extract_frames(self):
        if self.extraction_thread and self.extraction_thread.isRunning():
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Extracting frames...")
        self.session_export_status.setText("Extracting")
        self.extract_btn.setEnabled(False)

        fmt = self.format_combo.currentText()
        self.extraction_thread = ExtractionThread(
            self.video_path, self.output_dir, self.resolution, fmt,
            self.extract_fps, self.total_frames
        )
        self.extraction_thread.progress.connect(self.progress_bar.setValue)
        self.extraction_thread.finished.connect(self.extraction_finished)
        self.extraction_thread.error.connect(self.extraction_error)
        self.extraction_thread.start()

    def recombine_frames(self):
        if self.recombination_thread and self.recombination_thread.isRunning():
            return

        out_fmt = self.recom_combo.currentText()
        if out_fmt == "None":
            return

        output_file = (self.output_dir / f"recombined.{out_fmt}"
                       if self.output_dir else Path(f"recombined.{out_fmt}"))

        try:
            fps = float(self.fps_input.text()) if self.fps_input.text().strip() else 30.0
            if fps <= 0:
                raise ValueError
            duration = float(self.duration_input.text()) if self.duration_input.text().strip() else None
            if duration is not None and duration <= 0:
                raise ValueError
        except ValueError:
            InfoBar.warning(
                title="Invalid recombine settings",
                content="FPS and duration must be positive numbers.",
                parent=self,
                duration=4000,
                position=InfoBarPosition.TOP_RIGHT,
            )
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Recombining frames...")
        self.session_export_status.setText("Encoding")
        self.recom_btn.setEnabled(False)

        self.recombination_thread = RecombinationThread(
            self.frames_dir, output_file, out_fmt, fps, duration
        )
        self.recombination_thread.progress.connect(self.progress_bar.setValue)
        self.recombination_thread.progress_text.connect(self.progress_label.setText)
        self.recombination_thread.finished.connect(self.recombination_finished)
        self.recombination_thread.error.connect(self.recombination_error)
        self.recombination_thread.start()

    def extraction_finished(self, message):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Progress: Idle")
        self.session_export_status.setText("Extracted")
        self._blue_info("Extraction complete", message, duration=5000)
        self.extract_btn.setEnabled(True)

    def recombination_finished(self, message):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Progress: Idle")
        self.session_export_status.setText("Complete")
        self._blue_info("Recombine complete", message, duration=5000)
        self.recom_btn.setEnabled(True)

    def extraction_error(self, message):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Progress: Idle")
        self.session_export_status.setText("Failed")
        InfoBar.error(
            title="Extraction failed",
            content=message,
            parent=self,
            duration=5000,
            position=InfoBarPosition.TOP_RIGHT,
        )
        self.extract_btn.setEnabled(True)

    def recombination_error(self, message):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Progress: Idle")
        self.session_export_status.setText("Failed")
        InfoBar.error(
            title="Recombine failed",
            content=message,
            parent=self,
            duration=5000,
            position=InfoBarPosition.TOP_RIGHT,
        )
        self.recom_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoFrameExtractor()
    window.show()
    sys.exit(app.exec())
