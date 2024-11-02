import re
import glob
import warnings
import dcm2niix
import numpy as np
import importlib.resources
from pathlib import Path
from customtkinter import CTkEntry, CTkFrame, CTkButton
from niftiview.utils import load_json, save_json
DATA_PATH = str(importlib.resources.files('niftiview_app')) + '/data'
CONFIG_DICT = load_json(f'{DATA_PATH}/config.json')
LAYER_ATTRIBUTES = ('resizing', 'cmap', 'transp_if', 'qrange', 'vrange', 'is_atlas')
SAVE_RESET_ATTRIBUTES = ('filepaths_view1', 'filepaths_view2', 'origin', 'resizing', 'cmap',
                         'transp_if', 'qrange', 'vrange', 'is_atlas', 'annotation_dict')
GRID_ATTRIBUTES = ['origin', 'layout', 'height', 'squeeze', 'coord_sys', 'glass_mode', 'equal_hist', 'alpha',
                   'crosshair', 'fpath', 'coordinates', 'header', 'histogram', 'cbar', 'title', 'fontsize',
                   'linecolor', 'linewidth', 'tmp_height', 'nrows', 'cbar_vertical', 'cbar_pad', 'cbar_pad_color',
                   'cbar_x', 'cbar_y', 'cbar_width', 'cbar_length', 'cbar_label', 'cbar_ticks'] + list(LAYER_ATTRIBUTES)
LINECOLORS = ('white', 'gray', 'black')
TMP_HEIGHTS = (1080, 720, 480, 360, 240)
PADCOLORS = ('black', 'white', 'gray', 'transparent')


def set_fullscreen(event=None, app=None):
    if app is not None:
        app.master.wm_attributes('-fullscreen', not app.master.attributes('-fullscreen'))


def parse_dnd_filepaths(filepaths):
    return [fp.strip('{}') for fp in re.findall(r'{[^}]*}|\S+', filepaths)]


def get_window_frame(size, exp=12):
    x, y = np.meshgrid(np.linspace(-1, 1, size[0]), np.linspace(-1, 1, size[1]), indexing='xy', copy=False)
    frame = (x ** exp + y ** exp) / 2
    return (255 * (1 - frame)).astype(np.uint8)


def dcm2nii(input_filepath=None, output_dirpath=None):
    if Path(input_filepath).is_dir() or (Path(input_filepath).is_file() and input_filepath.endswith('.dcm')):
        if Path(output_dirpath).is_dir():
            dcm2niix.main(['-o',  output_dirpath, input_filepath])
        else:
            warnings.warn(f'{output_dirpath} is not an existing directory')
    else:
        warnings.warn(f'{input_filepath} is not a dicom file')
    return sorted(glob.glob(f'{output_dirpath}/*.ni*'))


def debounce(app, func, wait=1):
    def debounced(event):
        def call_it():
            func(app)
            debounced._timer = None
        if debounced._timer:
            app.after_cancel(debounced._timer)
        debounced._timer = app.after(wait, call_it)
    debounced._timer = None
    return debounced


class CTkSpinbox(CTkFrame):
    def __init__(self, *args, width=140, height=30, from_=None, to=None, is_float=False, increment=1, command=None,
                 **kwargs):
        super().__init__(*args, width=width, height=height, **kwargs)
        self.from_ = from_
        self.to = to
        self.is_float = is_float
        self.increment = float(increment) if is_float else int(increment)
        self.command = command
        self.configure(fg_color=('gray78', 'gray28'))  # set frame color
        self.grid_columnconfigure((0, 2), weight=0)  # buttons don't expand
        self.grid_columnconfigure(1, weight=1)  # entry expands
        self.subtract_button = CTkButton(self, text='-', width=height-6, height=height-6,
                                         command=lambda: self.button_callback(-1))
        self.subtract_button.grid(row=0, column=0, padx=(3, 0))
        self.entry = CTkEntry(self, width=width-(2*height), height=height-6, border_width=0)
        self.entry.grid(row=0, column=1, columnspan=1, padx=3, sticky='ew')
        self.entry.bind('<Return>', lambda e: self.button_callback(sign=0))
        self.add_button = CTkButton(self, text='+', width=height-6, height=height-6,
                                    command=lambda: self.button_callback(1))
        self.add_button.grid(row=0, column=2, padx=(0, 3))
        self.entry.insert(0, '0')

    def button_callback(self, sign=1):
        try:
            self.set(self.get() + sign * self.increment)
        except ValueError:
            return
        if self.command is not None:
            self.command(self.get())

    def get(self):
        try:
            return float(self.entry.get()) if self.is_float else int(self.entry.get())
        except ValueError:
            return None

    def set(self, value):
        if self.from_ is not None:
            value = max(value, self.from_)
        if self.to is not None:
            value = min(value, self.to)
        if value is not None:
            self.entry.delete(0, 'end')
            self.entry.insert(0, f'{float(value):.2f}' if self.is_float and value < 1000 else str(int(value)))

    def configure(self, require_redraw=False, **kwargs):
        if 'state' in kwargs:
            self._state = kwargs.pop('state')
            require_redraw = True
        if 'command' in kwargs:
            self.command = kwargs.pop('command')
        super().configure(require_redraw=require_redraw, **kwargs)
