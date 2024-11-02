# Installation Manual 🛠️
The basic installation instructions (see [README](https://github.com/codingfisch/niftiview_app/blob/main/README.md)) are
- Windows 🪟: [**Download**](https://github.com/codingfisch/niftiview_app/releases), unzip, double-click, ignore potential virus alert 🏁
- Linux 🐧: [**Download**](https://github.com/codingfisch/niftiview_app/releases), unzip, open terminal and run `chmod +x NiftiView.bin`, double-click 🏁
- macOS 🍏: Open terminal, install via `pip install niftiview-app`, run via `niftiview-app` 🏁

This manual provides **additional instructions** to make NiftiView

- feel like a proper app
- the standard app for `.nii` files 🧠

## Windows 🪟
- Move `NiftiView.exe` to an appropriate location
  - Admin users: Create the folder `NiftiView` in `C:\Program Files` and move `.exe` there
  - Regular users: Create a folder (e.g. `Tools`) in `C:\Users\YOUR_USER` and move `.exe` there
- To access NiftiView from the Taskbar, right-click on `NiftiView.exe` and select **Pin to Start**
- Make it the standard app for `.nii` files 🧠 
  - Right-click on a `.nii` file, **Open with**, **Choose another app**, **More apps**, check **Always use this app to open...** 🏁

## Linux 🐧
- Move `NiftiView.bin` to an appropriate location
  - Admin users: I recommend `/usr/local/bin` but Linux users often have own opinions 🤓
  - Regular users: I recommend `~/.local/bin`...
- Download `niftiview.png` [here](https://github.com/codingfisch/niftiview_app/blob/main/niftiview_app/data/niftiview.png) and move it to
  - `/usr/share/icons` if you saved `NiftiView.bin` in `/usr/local/bin`
  - `~/.local/share/icons` if you saved `NiftiView.bin` in `~/.local/bin`
- Open a terminal and then run...
```bash
nano ~/.local/share/applications/niftiview.desktop
```
- Add the following content to the file
```ini
[Desktop Entry]
Version=0.1.0
Name=NiftiView
Exec=/path/to/NiftiView.bin
Icon=/path/to/niftiview.png
Type=Application
Categories=Utility;
```
- Replace `/path/to/NiftiView.bin` and `/path/to/niftiview.png` with the actual paths
- Make it the standard app for `.nii` files 🧠 
  - Right-click on a `.nii` file, **Properties**, **Open With** tab, choose **NiftiView**, **Set as default** 🏁

## macOS 🍏
- Open a terminal and run `pip install niftiview-app` installing NiftiView in the default Python of macOS
- Launch macOS Automator (e.g. from the Applications folder)
  - Choose **New Document** and select **Application** as the type
  - Add a **Run Shell Script** Action
  - Set **Pass input** to **as arguments**
  - Enter `niftiview-app "$@"` in the script
  - Go to **File > Save** and name it `NiftiView`
  - Save it in the **Applications** folder
- Download `niftiview.icns` [here](https://github.com/codingfisch/niftiview_app/blob/main/niftiview_app/data/niftiview.icns)
- Right-click on the NiftiView file in the **Applications** folder, **Get info**, drag `niftiview.icns` to the small icon at the top left
- Make it the standard app for `.nii` files 🧠 
  - Right-click on a `.nii` file, **Get info**, **Open with**, select **NiftiView**, check **Change All** 🏁
