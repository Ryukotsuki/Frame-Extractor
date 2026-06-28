<div align="center">

<img height="307" alt="Frame Extractor" src="https://github.com/user-attachments/assets/a2600e5d-e9b5-4c22-8ca8-80937fa51197" />

# 🎬 Frame Extractor

**A modern Windows desktop app for extracting frames from videos or GIFs, recombining frame folders, and generating login-animation XML.**

[![Downloads][downloads-shield]][downloads-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

</div>

---

## ✨ Overview

**Frame Extractor** is a Python desktop application built with **PySide6**, **PySide6-Fluent-Widgets**, and **MoviePy**. It gives you a clean visual workflow for loading media, exporting frames, adjusting extraction settings, and optionally recombining frames back into GIF or MP4.

It is designed for local Windows media workflows, with no cloud upload required.

---

## 🚀 Features

- 🎥 **Video and GIF input**
  - Supports MP4, AVI, MOV, MKV, and GIF
  - Displays FPS, frame estimate, resolution, and duration

- 🖼️ **Flexible frame extraction**
  - Export frames as JPG or PNG
  - Keep original resolution or resize to 1080p, 1440p, 4K, or a custom size
  - Extract at original FPS, a custom FPS, or a target total frame count

- 🔄 **Frame recombination**
  - Convert numbered frame folders back into GIF or MP4
  - Control output FPS or target duration
  - Progress feedback while processing

- 🧩 **Login Animation XML Generator**
  - Built-in companion tool for creating `login-animation.xml`
  - Useful for PokeMMO animated login screen workflows

- 🎨 **Modern Fluent interface**
  - Dark professional UI
  - Responsive layout for resized or maximized windows
  - Styled dialogs, update prompts, dropdowns, and progress states

- 🔔 **In-app updates**
  - Checks GitHub releases for new versions
  - Supports folder-based release ZIP updates

---

## 📸 Media Showcase

<img width="1062" height="907" alt="Frame Extractor" src="https://github.com/user-attachments/assets/45e95225-f753-4d14-9188-cd209af4ec22" />

<img width="642" height="552" alt="Login Animation XML Generator" src="https://github.com/user-attachments/assets/b662dd28-aac6-4402-b69c-c774abcf3be9" />

---

## ⬇️ Download

Download the latest packaged release from the [Releases page](https://github.com/Ryukotsuki/Frame-Extractor/releases).

1. Download `FrameExtractor-<version>.zip`
2. Extract the full folder
3. Run `FrameExtractor.exe`

> Do not run the executable directly from inside the ZIP. Extract it first so bundled files and update support work correctly.

---

## 🧭 Quick Start

1. Click **Select Video or GIF**
2. Choose your resolution, frame format, FPS, or target frame count
3. Select an output folder
4. Click **Extract Frames**
5. Optional: choose a frames folder and recombine to GIF or MP4

Extracted frames are saved into a `frames` folder inside your selected output directory.

---

## 🛠️ Build From Source

### Requirements

- Windows 10/11
- Python 3.12 or newer recommended
- Git, if cloning from GitHub

### Setup

```powershell
git clone https://github.com/Ryukotsuki/Frame-Extractor.git
cd Frame-Extractor
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python "Frame Extractor.py"
```

### Create a Release Build

```powershell
.\Build Frame Extractor.bat
```

The build script creates:

- `dist\FrameExtractor\` - packaged app folder
- `dist\FrameExtractor-<version>.zip` - GitHub release ZIP

---

## 📦 Built With

| Package | Purpose |
| --- | --- |
| PySide6 | Qt desktop UI |
| PySide6-Fluent-Widgets | Fluent-style widgets |
| MoviePy | Video reading and encoding |
| imageio | Frame writing |
| imageio-ffmpeg | Bundled FFmpeg support |
| Pillow | Image and GIF processing |
| proglog | Encoding progress |
| PyInstaller | Windows packaging |

---

## 💖 Support and Contributions

If you enjoy **Frame Extractor** and want to support development, donations are appreciated:

[Donate via PayPal](https://paypal.me/Ryukotsuki?country.x=US&locale.x=en_US)

Have questions, suggestions, or want to share what you made?

[![Join Discord](https://github.com/user-attachments/assets/09fb5822-5e82-431b-b9cc-bbd4111ba48b)](https://discord.gg/HdfjKbPNc9)

---

## ⭐ Star the Project

If **Frame Extractor** helps you, consider starring the repository. It helps others find the project and supports future development.

[downloads-shield]: https://img.shields.io/github/downloads/Ryukotsuki/Frame-Extractor/total?style=for-the-badge
[downloads-url]: https://github.com/Ryukotsuki/Frame-Extractor/releases
[stars-shield]: https://img.shields.io/github/stars/Ryukotsuki/Frame-Extractor.svg?style=for-the-badge
[stars-url]: https://github.com/Ryukotsuki/Frame-Extractor/stargazers
[issues-shield]: https://img.shields.io/github/issues/Ryukotsuki/Frame-Extractor.svg?style=for-the-badge
[issues-url]: https://github.com/Ryukotsuki/Frame-Extractor/issues
