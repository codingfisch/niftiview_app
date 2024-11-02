import re
import glob
import warnings
import dcm2niix
import numpy as np
import importlib.resources
from csv import writer
from pathlib import Path
from customtkinter import CTkEntry, CTkFrame, CTkButton
from niftiview.core import TEMPLATES, TEMPLATE_DEFAULT
from niftiview.image import QRANGE, CMAP, CMAP_MASK
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


class Config:
    def __init__(self, scaling=None, appearance_mode='dark', filepaths_view1=None, filepaths_view2=None, view=1, page=0,
                 max_samples=4, origin=None, layout='sagittal++', height=600, squeeze=False, coord_sys='array_mm',
                 glass_mode=None, annotations=False, resizing=None, cmap=None, transp_if=None, qrange=None, vrange=None,
                 equal_hist=False, is_atlas=None, alpha=.5, crosshair=False, fpath=0, coordinates=False, header=False,
                 histogram=False, cbar=False, title=None, fontsize=20, linecolor='white', linewidth=2, tmp_height=360,
                 nrows=None, cbar_vertical=True, cbar_pad=0, cbar_pad_color='k', cbar_x=.9, cbar_y=.5, cbar_width=.05,
                 cbar_length=.8, cbar_label=None, cbar_ticks=None, annotation_dict=None):
        self.scaling = scaling
        self.appearance_mode = appearance_mode
        self.filepaths_view1 = [[TEMPLATES[TEMPLATE_DEFAULT]]] if filepaths_view1 is None else filepaths_view1
        self.filepaths_view2 = [[TEMPLATES[TEMPLATE_DEFAULT]]] if filepaths_view2 is None else filepaths_view2
        self.view = view
        self.page = page
        self.max_samples = max_samples
        self.origin = origin or [0, 0, 0, 0]
        self.layout = layout
        self.height = height
        self.squeeze = squeeze
        self.coord_sys = coord_sys
        self.glass_mode = glass_mode
        self.annotations = annotations
        self.resizing = resizing or [1] + (self.n_layers - 1) * [0]
        self.cmap = cmap or [CMAP] + (self.n_layers - 1) * [CMAP_MASK]
        self.transp_if = transp_if or [None] + (self.n_layers - 1) * ['=0']
        self.qrange = self.n_layers * [None] if qrange is None else qrange
        self.vrange = vrange or self.n_layers * [None]
        self.is_atlas = is_atlas or self.n_layers * [False]
        self.equal_hist = equal_hist
        self.alpha = alpha
        self.crosshair = crosshair
        self.fpath = fpath
        self.coordinates = coordinates
        self.header = header
        self.histogram = histogram
        self.cbar = cbar
        self.title = title
        self.fontsize = fontsize
        self.linecolor = linecolor
        self.linewidth = linewidth
        self.tmp_height = tmp_height
        self.nrows = nrows
        self.cbar_vertical = cbar_vertical
        self.cbar_pad = cbar_pad
        self.cbar_pad_color = cbar_pad_color
        self.cbar_x = cbar_x
        self.cbar_y = cbar_y
        self.cbar_width = cbar_width
        self.cbar_length = cbar_length
        self.cbar_label = cbar_label
        self.cbar_ticks = cbar_ticks
        self.annotation_dict = {fps[0]: 0 for fps in self.filepaths} or annotation_dict

    @property
    def filepaths(self):
        return [self.filepaths_view1, self.filepaths_view2][self.view - 1]

    @property
    def toplevel_filepaths(self):
        return [fpaths[-1] for fpaths in self.filepaths]

    @property
    def n_layers(self):
        return len(self.filepaths[0])

    @property
    def n_pages(self):
        return (len(self.filepaths) - 1) // self.max_samples + 1

    def get_filepaths(self, view=None):
        view = view or self.view
        fpaths = [self.filepaths_view1, self.filepaths_view2][view - 1]
        fpaths_pages = [fpaths[i:i + self.max_samples] for i in range(0, len(fpaths), self.max_samples)]
        return fpaths_pages[min(self.page, len(fpaths_pages) - 1)]

    def add_filepaths(self, fpaths, is_mask=False):
        fpaths = sorted(glob.glob(fpaths)) if isinstance(fpaths, str) else fpaths
        if is_mask:
            assert len(fpaths) == len(self.filepaths) or len(fpaths) == 1 or len(self.filepaths) == 1, \
                f'{len(fpaths)} filepaths given. Must be 1 or {len(self.filepaths)} (no. of images) to be added as masks'
            if len(fpaths) > 1 and len(self.filepaths) == 1:
                setattr(self, f'filepaths_view{self.view}', len(fpaths) * self.filepaths)
            self.add_mask_layer()
            fpaths = len(self.filepaths) * fpaths if len(fpaths) == 1 else fpaths
            setattr(self, f'filepaths_view{self.view}', [fps + [fp] for fps, fp in zip(self.filepaths, fpaths)])
        else:
            self.remove_mask_layers()
            setattr(self, f'filepaths_view{self.view}', [[fp] for fp in fpaths])
            self.page = 0
            if self.view == 1:
                self.annotation_dict = {fp: 0 for fp in fpaths}

    def set_max_samples(self, max_samples):
        self.max_samples = max_samples
        self.nrows = None

    def set_title(self, title):
        if '|' in title:
            title = title.split('|')
            title += (len(self.get_filepaths()) - len(title)) * [None]
        self.title = title

    def set_cbar_ticks(self, ticks):
        if ':' in ticks:
            ticks = {float(s.split(':')[0]): s.split(':')[1] for s in ticks.split('|')}
        elif not ticks:
            ticks = None
        else:
            ticks = [float(s) for s in ticks.split('|')]
        self.cbar_ticks = ticks

    def add_mask_layer(self):
        self.resizing = self.resizing + [0 if self.n_layers == 1 else self.resizing[-1]]
        self.cmap = self.cmap + [CMAP_MASK if self.n_layers == 1 else self.cmap[-1]]
        self.transp_if = self.transp_if + ['=0' if self.n_layers == 1 else self.transp_if[-1]]
        self.qrange = self.qrange + [QRANGE[1] if self.n_layers == 1 else self.qrange[-1]]
        self.vrange = self.vrange + [None]
        self.is_atlas = self.is_atlas + [True]

    def remove_mask_layers(self):
        setattr(self, f'filepaths_view{self.view}', [fpaths[:1] for fpaths in self.filepaths])
        for layer_attr in LAYER_ATTRIBUTES:
            setattr(self, layer_attr, getattr(self, layer_attr)[:1])

    def set_layer_attribute(self, key, value, is_mask=False):
        if self.n_layers > 1 or not is_mask:
            assert key in LAYER_ATTRIBUTES, f'Attribute must be in {LAYER_ATTRIBUTES} but is {key}'
            attr = getattr(self, key)
            attr = self.n_layers * [None] if attr is None else attr
            attr[-1 if is_mask else 0] = value
            setattr(self, key, attr)

    def save_annotations(self, filepath):
        with open(filepath, 'w', newline='') as file:
            csv_writer = writer(file)
            csv_writer.writerow(['filepath', 'annotation'])
            for key, value in self.annotation_dict.items():
                csv_writer.writerow([key, value])

    def save(self, filepath):
        save_dict = self.to_dict()
        save_dict = {k: None if k in SAVE_RESET_ATTRIBUTES else v for k, v in save_dict.items()}
        save_json(save_dict, filepath)

    def to_dict(self, grid_kwargs_only=False):
        config_dict = {}
        for k in vars(self):
            if not k.startswith('_') and (not grid_kwargs_only or k in GRID_ATTRIBUTES):
                config_dict.update({k: getattr(self, k)})
        return config_dict

    @classmethod
    def from_json(cls, filepath):
        config_dict = load_json(filepath)
        return cls(**config_dict)

    @classmethod
    def from_dict(cls, config_dict):
        return cls(**config_dict)
