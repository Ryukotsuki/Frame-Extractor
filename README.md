<p align="center">
  <img src="https://github.com/user-attachments/assets/a2600e5d-e9b5-4c22-8ca8-80937fa51197" alt="Frame Extractor preview" height="320" />
</p>

<h1 align="center">Frame Extractor</h1>

<p align="center">
  A modern Windows desktop app for extracting frames from videos or GIFs, recombining frame folders, and generating login-animation XML.
</p>

<p align="center">
  <a href="https://github.com/Ryukotsuki/Frame-Extractor/releases"><img src="https://img.shields.io/github/v/release/Ryukotsuki/Frame-Extractor?style=for-the-badge&label=Latest%20Release" alt="Latest release"></a>
  <a href="https://github.com/Ryukotsuki/Frame-Extractor/releases"><img src="https://img.shields.io/github/downloads/Ryukotsuki/Frame-Extractor/total?style=for-the-badge" alt="Downloads"></a>
  <a href="https://github.com/Ryukotsuki/Frame-Extractor/stargazers"><img src="https://img.shields.io/github/stars/Ryukotsuki/Frame-Extractor.svg?style=for-the-badge" alt="Stars"></a>
  <a href="https://github.com/Ryukotsuki/Frame-Extractor/issues"><img src="https://img.shields.io/github/issues/Ryukotsuki/Frame-Extractor.svg?style=for-the-badge" alt="Issues"></a>
</p>

---

## ✨ Features

- 🎥 **Video and GIF Input**  
  Load common media formats including MP4, AVI, MOV, MKV, and GIF.

- 📊 **Media Details at a Glance**  
  View FPS, estimated frame count, resolution, and duration before exporting.

- 🖼️ **Flexible Frame Extraction**  
  Export frames as JPG or PNG while keeping the original resolution or resizing to 1080p, 1440p, 4K, or a custom size.

- 🎚️ **FPS and Frame Count Controls**  
  Extract at the original FPS, a custom FPS, or a target total frame count.

- 🔄 **Frame Recombination**  
  Convert numbered frame folders back into GIF or MP4 with output FPS or target duration controls.

- 🧩 **Login Animation XML Generator**  
  Includes a companion tool for generating `login-animation.xml` for PokeMMO animated login screen workflows.

- 🎨 **Modern Fluent Interface**  
  Built with PySide6 and Fluent widgets for a clean dark UI, responsive layout, styled dialogs, and smooth progress states.

- 🔔 **In-App Update Checks**  
  Checks GitHub releases for newer versions and supports folder-based release ZIP updates.

- 🔒 **Local-First Workflow**  
  Media is processed locally on your machine with no cloud upload required.

---

## 📸 Preview

<p align="center">
  <img width="1062" height="907" alt="Frame Extractor screenshot" src="https://github.com/user-attachments/assets/45e95225-f753-4d14-9188-cd209af4ec22" />
</p>

<p align="center">
  <img width="642" height="552" alt="Login Animation XML Generator screenshot" src="https://github.com/user-attachments/assets/b662dd28-aac6-4402-b69c-c774abcf3be9" />
</p>

---

## 🚀 Getting Started

### ⬇️ Download

Download the latest packaged release from the [Releases page](https://github.com/Ryukotsuki/Frame-Extractor/releases).

### ⚡ Quick Start

1. Download `FrameExtractor-<version>.zip`.
2. Extract the full folder anywhere you like.
3. Run `FrameExtractor.exe`.
4. Click **Select Video or GIF**.
5. Choose your output settings.
6. Select an output folder.
7. Click **Extract Frames**.

> Do not run the executable directly from inside the ZIP. Extract it first so bundled files and update support work correctly.

---

## 🧭 Common Workflows

### Extract Frames

1. Select a video or GIF.
2. Choose JPG or PNG.
3. Pick the original resolution, a preset size, or a custom size.
4. Choose original FPS, custom FPS, or a target frame count.
5. Select an output folder and start extraction.

Extracted frames are saved into a `frames` folder inside your selected output directory.

### Recombine Frames

1. Select a folder containing numbered frame images.
2. Choose GIF or MP4 output.
3. Set output FPS or target duration.
4. Start recombination and wait for the progress to finish.

### Generate Login Animation XML

1. Open the **Login XML** tool.
2. Configure the animation frame data.
3. Generate `login-animation.xml`.
4. Use it in your PokeMMO animated login screen workflow.

---

## 🛠 Build From Source

### Requirements

- Windows 10/11
- Python 3.12 or newer
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

### Build

```powershell
.\Build Frame Extractor.bat
```

The build script creates:

```text
dist\FrameExtractor\              # Packaged app folder
dist\FrameExtractor-<version>.zip  # GitHub release ZIP
```

---

## 📦 Built With

| Package | Purpose |
| --- | --- |
| PySide6 | Qt desktop interface |
| PySide6-Fluent-Widgets | Fluent-style controls |
| MoviePy | Video reading and encoding |
| imageio | Frame writing |
| imageio-ffmpeg | FFmpeg support |
| Pillow | Image and GIF processing |
| proglog | Encoding progress |
| PyInstaller | Windows packaging |

---

## 📂 Project Structure

```text
Frame Extractor/
├─ Images/                  # App icons and image assets
├─ Showcase/                # README preview images
├─ Source/                  # Companion source files
├─ dist/                    # Packaged build output
├─ licenses/                # License files
├─ requirements.txt         # Python dependencies
├─ Frame Extractor.py       # Main app entry point
├─ FrameExtractor.spec      # PyInstaller spec
└─ version_info.txt         # Windows executable version metadata
```

---

## 📝 Notes

- 🪟 **Windows only**: Frame Extractor is designed for Windows desktop workflows.
- 📁 **Folder releases**: Keep `FrameExtractor.exe` together with its bundled files.
- 🎞️ **Encoding support**: GIF and MP4 recombination depend on the included media libraries and FFmpeg support.
- 🔄 **Updates**: Use the in-app update check or download the latest release manually from GitHub.
- 🧪 **Large exports**: High-resolution or high-FPS exports can create many files and may take time.

---

## 📜 License

Frame Extractor is licensed under the **GNU Lesser General Public License v3.0**.

See the `licenses` folder for the full LGPLv3 license text.

---

## 💖 Support

If Frame Extractor helps you, a star on GitHub goes a long way.

- ⭐ Star the repository
- 🐛 Report bugs through [Issues](https://github.com/Ryukotsuki/Frame-Extractor/issues)
- 💡 Suggest improvements or new features
- 💸 [Donate via PayPal](https://paypal.me/Ryukotsuki?country.x=US&locale.x=en_US)

### 💬 Community

Have questions, feedback, or want to share what you made? Join the Discord:

<p align="center">
  <a href="https://discord.gg/HdfjKbPNc9">
    <img src="https://github.com/user-attachments/assets/09fb5822-5e82-431b-b9cc-bbd4111ba48b" alt="Join Discord" />
  </a>
</p>

---

<p align="center">
  Built for clean frame exports, smooth recombines, and better media workflows. ✨
</p>
