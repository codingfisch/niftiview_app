![niftiview_logo_transparent_small](https://github.com/user-attachments/assets/109d0dda-6704-4d9c-9c14-4b29aaa1a52f)

NiftiView is a medical 3D image viewer **made for amateurs** 👨, **clinicians** 👩‍⚕️, **scientists** 👨‍🔬 and **coders** 👩‍💻

**Highlight features** for each user group are

- 👨 **Drag&Drop** to easily **view multiple** 3D images in a **beautiful layout** and save as a **GIF**
- 👩‍⚕️ **Shortcuts** to quickly set up **optimal contrasts** by intensity windowing and **histogram equalization**
- 👨‍🔬 **Custom image layers and overlays** (crosshair, colorbar...) to create **publication-ready figures**
- 👩‍💻 Usable via **Python and Command Line Interface** (take a look at [the underlying Python package](https://github.com/codingfisch/niftiview))

Besides these highlights, NiftiView also **covers the basics**
- 💾 Supports **NIfTI** `.nii`/`.nii.gz`, **NumPy** `.npy`, **DICOM** and some **older 3D image formats**
- 🖼️ **High image quality** via Lanczos interpolation
- 📥 **Easy installation** for Windows and Linux: [**Download**](https://github.com/codingfisch/niftiview_app/releases), unzip, double-click 🏁

Learn how to use NiftiView via [the **YouTube-Tutorial**](https://www.youtube.com/) 💡

## Installation 🛠️
### Windows 🪟 or Linux 🐧
Download the app [**here**](https://github.com/codingfisch/niftiview_app/releases), unzip the downloaded file and double-click either
- NiftiView.exe (+ ignore potential virus alert, if you are using Windows)
- NiftiView.bin (+ previously run `chmod +x NiftiView.bin` in a terminal, if you are using Linux) 

to run NiftiView 🧠 If you like it, check out [this short manual](https://github.com/codingfisch/niftiview_app/blob/main/install.md) to finalize the installation 🛠️
### The Python way 🐍
Users of macOS 🍏 and/or [Pythonistas](https://en.wiktionary.org/wiki/Pythonista) just **install it in the terminal** via
```bash
pip install niftiview-app
```
and **run it** via
```bash
niftiview-app
```
Some extra steps to make NiftiView feel like a macOS app are provided [here](https://github.com/codingfisch/niftiview_app/blob/main/install.md) 🛠️

### Bugfixes 🐛
- If the app does not start, missing packages can be the issue. To fix that:
  - On Linux: Run `sudo apt install libcairo2-dev pkg-config python3-dev`
  - On macOS: Run `brew install cairo pkg-config tcl-tk python-tk`
- If the app [looks grainy](https://github.com/ContinuumIO/anaconda-issues/issues/6833) in a conda env, run `conda install -c conda-forge tk=*=xft_*` to fix it

## Backstory 📖
Read about the long winding road from an annoying problem during my PhD to the release of NiftiView in [my blog](https://codingfisch.github.io/) (will be posted soon 🤝).
