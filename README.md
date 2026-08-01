<div align="center">

# 🌌 ECHOES
### *A Minimalist, Secure, and Distraction-Free Desktop Journal*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://www.qt.io/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<br />

<p align="center">
  <b>ECHOES</b> is a sleek desktop journaling environment crafted for personal reflection. Featuring modern UI aesthetics, dynamic theme controls, robust client-side PIN security, and hidden local database storage, ECHOES keeps your thoughts safe and private.
</p>

</div>

---

## 🖼️ Application Preview

<div align="center">
  <table border="0">
    <tr>
      <td width="50%" align="center">
        <b>🔐 Security Lock Screen</b><br/><br/>
        <img width="959" height="539" alt="image" src="https://github.com/user-attachments/assets/4225cf1a-cca3-4d3b-a46b-7672ad4fa046" />
      </td>
      <td width="50%" align="center">
        <b>📝 Distraction-Free Editor & Timeline</b><br/><br/>
        <img width="959" height="539" alt="image" src="https://github.com/user-attachments/assets/b5500787-3583-46c0-90b6-2a3cc9505be0" />
  </table>
</div>

---

## 📖 Table of Contents
1. [Overview & Philosophy](#-overview--philosophy)
2. [Why Python & PyQt6?](#-why-python--pyqt6)
3. [Key Features](#-key-features)
4. [Technology Stack & Libraries](#%EF%B8%8F-technology-stack--libraries)
5. [Architecture & Project Structure](#-architecture--project-structure)
6. [Security & Hidden Database System](#-security--hidden-database-system)
7. [Converting Python to Native `.exe`](#%EF%B8%8F-converting-python-to-native-exe)
8. [Installation & Local Setup](#-installation--local-setup)
9. [License](#-license)

---

## 💡 Overview & Philosophy

In an era of hyper-connected, ad-driven note-taking tools, **ECHOES** was built around a singular core principle: **absolute privacy meets serene simplicity**. 

Your personal thoughts shouldn't live on remote cloud servers or require third-party logins. ECHOES operates 100% offline, storing data locally in an obscured, OS-hidden database protected by a SHA-256 encrypted access code.

Entirely **vibecoded and developed by [itsvrtx](https://github.com/itsvrtx)**, the app ensures your personal thoughts don't live on remote cloud servers or require third-party logins. ECHOES operates 100% offline, storing data locally in an obscured, OS-hidden database protected by a SHA-256 encrypted access code.

---

## 🐍 Why Python & PyQt6?

### **Why Python?**
Python was chosen as the underlying language because of its unrivaled efficiency in rapid desktop application development, robust standard library support, and clean maintainability. 
* **Native OS Integration:** Python makes low-level operating system interactions—such as inspecting Windows environment variables (`%LOCALAPPDATA%`) and modifying C-level file attributes via `ctypes`—straightforward and reliable.
* **Built-in Data Integrity:** With embedded `sqlite3` and `hashlib` modules, Python handles data storage and cryptography out of the box without requiring bloated external dependencies.

### **Why PyQt6?**
While Python comes with default GUI kits like Tkinter, **PyQt6** was selected to deliver a commercial-grade, hardware-accelerated user experience:
* **Vector Graphics Rendering:** PyQt's `QSvgRenderer` dynamically draws crisp, scale-independent SVG icons across high-DPI Windows displays.
* **Deep QSS Styling:** Custom Qt Style Sheets (QSS) allow for fluid dark/light themes, subtle soft shadows, and clean glassmorphism container styling.

---

## ✨ Key Features

* 🔐 **4-Digit PIN Security:** App access is gated behind a SHA-256 hashed 4-digit code.
* 📁 **Hidden Local Storage:** Journal entries reside in an auto-generated, OS-hidden database file inside `%LOCALAPPDATA%\ECHOES`.
* 🎨 **Minimalist UI Design:** A soft, modern layout engineered to eliminate UI clutter while writing.
* 🔍 **Instant Search & Filtering:** Dynamic, low-latency entry search powered by indexed SQLite queries.
* 🏷️ **Categorization & Mood Tracking:** Tag journal entries with categories and mood indicators for organized retrieval.
* 🐣 **Hidden Easter Eggs:** Interactive micro-animations and hidden playful surprises are tucked away within the UI waiting to be discovered!
* ⚡ **Standalone Binary:** Fully packaged as an offline, single-directory executable (`.exe`)—no Python installation required for end-users.

---

## 🛠️ Technology Stack & Libraries

| Library / Tool | Purpose |
| :--- | :--- |
| **Python 3.11+** | Core programming language & runtime environment |
| **PyQt6** | GUI framework, rendering window layouts, widgets, and vector SVGs |
| **Pillow (PIL)** | In-memory image processing and multi-resolution `.ico` generation |
| **SQLite3** | Embedded, zero-configuration local relational database engine |
| **Hashlib** | One-way cryptographic hashing (`SHA-256`) for security PIN storage |
| **Ctypes** | Interfacing directly with `kernel32.dll` to manipulate Windows file attributes |
| **PyInstaller** | Compiling the Python codebase, assets, and standard libraries into a native Windows executable |

---

## 📂 Architecture & Project Structure

ECHOES adheres to a clean, modular structure that separates database logic, styling, assets, and UI components:

```text
echoes_app/
│
├── assets/
│   ├── logo.svg              # Primary vector logo used inside PyQt UI
│   └── logo (1).ico          # Multi-resolution Windows app & executable icon
│
├── database/
│   ├── database.py           # System path resolver (%LOCALAPPDATA%) & Windows file hiding
│   └── db_manager.py         # SQLite CRUD operations & SHA-256 security PIN logic
│
├── ui/
│   ├── __init__.py
│   ├── components.py         # Shared UI widgets & custom inputs
│   ├── editor.py             # Rich journal text editing interface
│   ├── lock_screen.py        # 4-digit security PIN unlock view
│   ├── main_window.py        # Primary container view manager
│   └── sidebar.py            # Entry history timeline & search bar
│
├── utils/
│   └── helpers.py            # PyInstaller runtime path resolver (sys._MEIPASS)
│
├── main.py                   # Application entry point
└── convert.py                # Developer script for rendering SVGs to .ico formats
```

---

## 🔒 Security & Hidden Database System

### 1. Obfuscated Storage Path
Rather than storing echoes_data.db directly alongside the binary (where it can be accidentally modified or deleted), ECHOES automatically creates a dedicated storage folder inside the user's local application data directory:
```text
C:\Users\<username>\AppData\Local\ECHOES\echoes_data.db
```

### 2. OS-Level Attribute Hiding
Using Python's ctypes library, ECHOES communicates directly with the Windows API to set the FILE_ATTRIBUTE_HIDDEN flag (0x02) on both the directory and the database file. This hides the file from standard File Explorer views unless "Show Hidden Files" is explicitly enabled.

### 3. Cryptographic Access Protection
Raw PINs are never stored in plain text.
When a user creates their 4-digit code, ECHOES computes its standard SHA-256 digest:

```text
Hash = SHA-256(PIN)
```
During authorization, the hash of the entered digits is calculated in-memory and compared against the stored hash in the app_security table.

---

## ⚙️ Converting Python to Native `.exe`
Because Windows natively requires a multi-resolution .ico format for binary icons, the build pipeline converts assets/logo.svg to assets/logo (1).ico using PyQt6's off-screen rasterizer and Pillow.

### Build Step 1: Generate ICO Asset
You can either use online converters like [FreeConvert](https://www.freeconvert.com) or use the following python script to convert your image to a .ico:

```python
import sys
from PIL import Image
import io
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer


def convert_svg_to_ico(svg_path: str, ico_path: str):
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        print(f"Error: Could not load {svg_path}")
        return
    size = 256
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))  # Transparent background

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    buffer = image.bits().asstring(image.sizeInBytes())
    pil_image = Image.frombuffer(
        "RGBA", (size, size), buffer, "raw", "BGRA", 0, 1
    )
    pil_image.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Successfully converted '{svg_path}' to '{ico_path}'!")


if __name__ == "__main__":
    convert_svg_to_ico("logo.svg", "logo.ico")
```
### Build Step 2: Compile with PyInstaller
Run the following command in PowerShell to clean past caches and build the standalone distribution:
```bash
pyinstaller --noconfirm --onefile --windowed --icon "assets/logo (1).ico" --add-data "assets;assets" main.py
```
--windowed: Suppresses the background command prompt console window.
--add-data "assets;assets": Bundles internal SVGs into PyInstaller's temporary sys._MEIPASS runtime buffer.
--icon: Sets the native binary icon displayed in Windows Explorer and the Taskbar.

---

## 🚀 Installation & Local Setup
### Prerequisites
Python 3.11+ installed on your machine.
### 1. Clone the Repository
```bash
git clone [https://github.com/itsvrtx/echoes-journal.git](https://github.com/itsvrtx/echoes-journal.git)
cd echoes-app
```
### 2. Create & Activate Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
```
### 3. Install Dependencies
```bash
pip install pyqt6 pillow pyinstaller
```
### 4. Launch Application
```bash
python main.py
```
---

## 📄 License
Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
