import numpy as np
from sys import argv
from time import time
from copy import deepcopy
from PIL import Image, ImageTk
from functools import partial
from warnings import filterwarnings
from webbrowser import open_new_tab
from customtkinter import (filedialog, set_appearance_mode, set_widget_scaling, CTk, CTkEntry, CTkFrame, CTkLabel,
                           CTkButton, CTkTabview, CTkToplevel, CTkOptionMenu, CTkCheckBox, CTkSlider, CTkSegmentedButton)
from tkinterdnd2 import DND_FILES, TkinterDnD
from CTkMenuBar import CTkMenuBar, CustomDropdownMenu
from niftiview.cli import save_gif, save_images_or_gifs
from niftiview.core import PLANES, ATLASES, TEMPLATES, RESIZINGS, LAYOUT_STRINGS, COORDINATE_SYSTEMS, GLASS_MODES
from niftiview.image import QRANGE, CMAPS_IMAGE, CMAPS_MASK
from niftiview.grid import NiftiImageGrid

from niftiview_app import __version__
from niftiview_app.utils import (DATA_PATH, PADCOLORS, LINECOLORS, CONFIG_DICT, TMP_HEIGHTS, LAYER_ATTRIBUTES, dcm2nii,
                                 debounce, set_fullscreen, get_window_frame, parse_dnd_filepaths, Config, CTkSpinbox)
PLANES_4D = tuple(list(PLANES) + ['time'])
SCALINGS = (.5, 2/3, .75, 1, 4/3, 1.5, 2)
OPTIONS = {'Main': ['Layout', '', 'Colormap', '', 'Mask colormap', '', 'Height', 'Max samples'],
           'Image': ['Equalize histogram', 'Percentile range', '', 'Value range', '', 'Transparent if', 'Resizing'],
           'Mask': ['Opacity [%]', 'Percentile range', '', 'Value range', '', 'Transparent if', 'Resizing', 'Is atlas'],
           'Overlay': ['Crosshair', 'Coordinates', 'Header', 'Histogram', 'Filepath', 'Title', 'Fontsize'],
           'Colorbar': ['Bar', 'Bar Position [%]', '', 'Bar Size [%]', '', 'Padding', 'Label', 'Ticks']}
OPTION_TABS = list(OPTIONS)
FILETYPES = [('Portable Network Graphics', '*.png'), ('JPEG', '*.jpg;*.jpeg'), ('Tagged Image File', '*.tiff;*.tif'),
             ('Portable Document Format', '*.pdf'), ('Scalable Vector Graphics', '*.svg'),
             ('Encapsulated PostScript', '*.eps'), ('PostScript', '*.ps')]
MENUBAR_ATTRIBUTES = ('tmp_height', 'linewidth', 'linecolor', 'cbar_pad_color',
                      'nrows', 'glass_mode', 'coord_sys', 'squeeze')
TUTORIAL_URL = 'https://www.youtube.com/'
HOMEPAGE_URL = 'https://github.com/codingfisch/niftiview_app'
AUTHOR_URL = 'https://github.com/codingfisch'
RELEASE_URL = f'{HOMEPAGE_URL}/releases/tag/v{__version__}'


class InputFrame(CTkFrame, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config')
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)
        self.grid_columnconfigure((0, 1), weight=1)
        grid_kwargs = {'sticky': 'nsew', 'padx': 1, 'pady': 1, 'columnspan': 2}
        self.view_button = CTkSegmentedButton(self, values=['View 1', 'View 2'])
        self.view_button.set(f'View {config.view}')
        self.view_button.grid(row=0, **grid_kwargs)
        self.image_entry = CTkEntry(self, placeholder_text='/path/to/images/*.nii (or drag&drop here)')
        self.image_entry.drop_target_register(DND_FILES)
        self.image_entry.grid(row=1, **grid_kwargs)
        self.mask_entry = CTkEntry(self, placeholder_text='/path/to/masks/*.nii (or drag&drop here)')
        self.mask_entry.drop_target_register(DND_FILES)
        self.mask_entry.grid(row=2, **grid_kwargs)


class OptionsFrame(CTkFrame):
    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config')
        super().__init__(*args, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.show_button = CTkButton(self, text='Show Options')
        self.alpha_spinbox = CTkSpinbox(self)       # little hack to easily
        self.alpha_spinbox.set(100 * config.alpha)  # enable clear masks
        self.show_button.grid(column=0, sticky='nsew')

    def show(self, config):
        self.show_button.destroy()
        self.tabview = CTkTabview(self, width=60)
        self.tabview.grid_columnconfigure(0, weight=1)
        for i, (tab, option_labels) in enumerate(OPTIONS.items()):
            setattr(self, f'tab{i}', self.tabview.add(tab))
            getattr(self, f'tab{i}').grid_columnconfigure(0, weight=1)
            getattr(self, f'tab{i}').grid_columnconfigure(1, weight=0)
            for row, label in enumerate(option_labels):
                label_attr = f'{label}_mask_label' if tab == 'Mask' else f'{label}_label'
                setattr(self, label_attr, CTkLabel(self.tabview.tab(tab), text=label))
                getattr(self, label_attr).grid(row=row, column=0, sticky='nsw')
        self.grid_kwargs = {'pady': 1, 'sticky': 'nswe'}
        self.grid_checkbox_kwargs = {'pady': self.grid_kwargs['pady'], 'sticky': 'nse'}
        self.checkbox_size = 25
        layout_str = LAYOUT_STRINGS[config.layout] if config.layout in LAYOUT_STRINGS else config.layout
        self.layout_options = CTkOptionMenu(self.tab0, values=list(LAYOUT_STRINGS), dynamic_resizing=False)
        self.layout_options.set(config.layout if layout_str in list(LAYOUT_STRINGS.values()) else None)
        self.layout_options.grid(row=0, column=1, **self.grid_kwargs)
        self.layout_entry = CTkEntry(self.tab0)
        self.layout_entry.insert('0', layout_str)
        self.layout_entry.grid(row=1, column=1, **self.grid_kwargs)
        self.cmap_options = CTkOptionMenu(self.tab0, values=list(CMAPS_IMAGE) + ['CATALOG'], dynamic_resizing=False)
        self.cmap_options.grid(row=2, column=1, **self.grid_kwargs)
        self.cmap_entry = CTkEntry(self.tab0)
        self.cmap_entry.grid(row=3, column=1, **self.grid_kwargs)
        self.cmap_mask_options = CTkOptionMenu(self.tab0, values=list(CMAPS_MASK) + ['CATALOG'], dynamic_resizing=False)
        self.cmap_mask_options.grid(row=4, column=1, **self.grid_kwargs)
        self.cmap_mask_entry = CTkEntry(self.tab0)
        self.cmap_mask_entry.grid(row=5, column=1, **self.grid_kwargs)
        self.height_spinbox = CTkSpinbox(self.tab0, from_=100, increment=100)
        self.height_spinbox.set(config.height)
        self.height_spinbox.grid(row=6, column=1, **self.grid_kwargs)
        self.max_samples_spinbox = CTkSpinbox(self.tab0, from_=1)
        self.max_samples_spinbox.set(config.max_samples)
        self.max_samples_spinbox.grid(row=7, column=1, **self.grid_kwargs)
        self.equal_hist_checkbox = CTkCheckBox(self.tab1, text='', width=self.checkbox_size, height=self.checkbox_size)
        if config.equal_hist:
            self.equal_hist_checkbox.select()
        self.equal_hist_checkbox.grid(row=0, column=1, **self.grid_checkbox_kwargs)
        self.qrange_start_spinbox = CTkSpinbox(self.tab1, from_=0, to=100, increment=1, is_float=True)
        self.qrange_start_spinbox.set(100 * (QRANGE[0][0] if config.qrange[0] is None else config.qrange[0][0]))
        self.qrange_start_spinbox.grid(row=1, column=1, columnspan=2, **self.grid_kwargs)
        self.qrange_stop_spinbox = CTkSpinbox(self.tab1, from_=0, to=100, increment=1, is_float=True)
        self.qrange_stop_spinbox.set(100 * (QRANGE[0][1] if config.qrange[0] is None else config.qrange[0][1]))
        self.qrange_stop_spinbox.grid(row=2, column=1, **self.grid_kwargs)
        self.vrange_start_spinbox = CTkSpinbox(self.tab1, increment=.5, is_float=True)
        self.vrange_start_spinbox.grid(row=3, column=1, **self.grid_kwargs)
        self.vrange_stop_spinbox = CTkSpinbox(self.tab1, increment=.5, is_float=True)
        self.vrange_stop_spinbox.grid(row=4, column=1, **self.grid_kwargs)
        self.transp_if_entry = CTkEntry(self.tab1, placeholder_text='<0.5')
        if config.transp_if[0] is not None:
            self.transp_if_entry.insert(0, config.transp_if[0])
        self.transp_if_entry.grid(row=5, column=1, **self.grid_kwargs)
        self.resizing_options = CTkOptionMenu(self.tab1, values=RESIZINGS, dynamic_resizing=False)
        self.resizing_options.set(RESIZINGS[config.resizing[0]])
        self.resizing_options.grid(row=6, column=1, **self.grid_kwargs)
        self.alpha_spinbox = CTkSpinbox(self.tab2, from_=0, to=100, increment=10, is_float=True)
        self.alpha_spinbox.set(100 * config.alpha)
        self.alpha_spinbox.grid(row=0, column=1, columnspan=2, **self.grid_kwargs)
        self.qrange_start_mask_spinbox = CTkSpinbox(self.tab2, from_=0, to=100, increment=1, is_float=True)
        self.qrange_start_mask_spinbox.set(100 * (config.qrange[-1][0] if len(config.qrange) > 1 else QRANGE[1][0]))
        self.qrange_start_mask_spinbox.grid(row=1, column=1, columnspan=2, **self.grid_kwargs)
        self.qrange_stop_mask_spinbox = CTkSpinbox(self.tab2, from_=0, to=100, increment=1, is_float=True)
        self.qrange_stop_mask_spinbox.set(100 * (config.qrange[-1][1] if len(config.qrange) > 1 else QRANGE[1][1]))
        self.qrange_stop_mask_spinbox.grid(row=2, column=1, columnspan=2, **self.grid_kwargs)
        self.vrange_start_mask_spinbox = CTkSpinbox(self.tab2, is_float=True)
        self.vrange_start_mask_spinbox.grid(row=3, column=1, columnspan=2, **self.grid_kwargs)
        self.vrange_stop_mask_spinbox = CTkSpinbox(self.tab2, is_float=True)#, increment=.2)
        self.vrange_stop_mask_spinbox.grid(row=4, column=1, columnspan=2, **self.grid_kwargs)
        self.transp_if_mask_entry = CTkEntry(self.tab2, placeholder_text='=0')
        if config.transp_if[-1] is not None:
            self.transp_if_mask_entry.insert(0, config.transp_if[-1])
        self.transp_if_mask_entry.grid(row=5, column=1, columnspan=2, **self.grid_kwargs)
        self.resizing_mask_options = CTkOptionMenu(self.tab2, values=RESIZINGS, dynamic_resizing=False)
        self.resizing_mask_options.set(RESIZINGS[config.resizing[-1]])
        self.resizing_mask_options.grid(row=6, column=1, columnspan=2, **self.grid_kwargs)
        self.is_atlas_checkbox = CTkCheckBox(self.tab2, text='', width=self.checkbox_size, height=self.checkbox_size)
        self.is_atlas_checkbox.select()
        self.is_atlas_checkbox.grid(row=7, column=1, columnspan=2, **self.grid_checkbox_kwargs)
        self.crosshair_checkbox = CTkCheckBox(self.tab3, text='', width=self.checkbox_size, height=self.checkbox_size)
        if config.crosshair:
            self.crosshair_checkbox.select()
        self.crosshair_checkbox.grid(row=0, column=1, **self.grid_checkbox_kwargs)
        self.coordinates_checkbox = CTkCheckBox(self.tab3, text='', width=self.checkbox_size, height=self.checkbox_size)
        if config.coordinates:
            self.coordinates_checkbox.select()
        self.coordinates_checkbox.grid(row=1, column=1, **self.grid_checkbox_kwargs)
        self.header_checkbox = CTkCheckBox(self.tab3, text='', width=self.checkbox_size, height=self.checkbox_size)
        if config.header:
            self.header_checkbox.select()
        self.header_checkbox.grid(row=2, column=1, **self.grid_checkbox_kwargs)
        self.histogram_checkbox = CTkCheckBox(self.tab3, text='', width=self.checkbox_size, height=self.checkbox_size)
        if config.histogram:
            self.histogram_checkbox.select()
        self.histogram_checkbox.grid(row=3, column=1, **self.grid_checkbox_kwargs)
        self.fpath_spinbox = CTkSpinbox(self.tab3, from_=0)
        self.fpath_spinbox.grid(row=4, column=1, **self.grid_kwargs)
        self.title_entry = CTkEntry(self.tab3)
        if config.title is not None:
            self.title_entry.insert('0', config.title)
        self.title_entry.grid(row=5, column=1, **self.grid_kwargs)
        self.fontsize_spinbox = CTkSpinbox(self.tab3, from_=1)
        self.fontsize_spinbox.set(config.fontsize)
        self.fontsize_spinbox.grid(row=6, column=1, **self.grid_kwargs)
        self.cbar_options = CTkOptionMenu(self.tab4, values=['', 'vertical', 'horizontal'], dynamic_resizing=False)
        self.cbar_options.set(['horizontal', 'vertical'][int(config.cbar_vertical)] if config.cbar else '')
        self.cbar_options.grid(row=0, column=1, **self.grid_kwargs)
        self.cbar_x_spinbox = CTkSpinbox(self.tab4, from_=0, to=100, is_float=True)
        self.cbar_x_spinbox.set(100 * config.cbar_x)
        self.cbar_x_spinbox.grid(row=1, column=1, **self.grid_kwargs)
        self.cbar_y_spinbox = CTkSpinbox(self.tab4, from_=0, to=100, is_float=True)
        self.cbar_y_spinbox.set(100 * config.cbar_y)
        self.cbar_y_spinbox.grid(row=2, column=1, **self.grid_kwargs)
        self.cbar_width_spinbox = CTkSpinbox(self.tab4, from_=0, to=100, is_float=True)
        self.cbar_width_spinbox.set(100 * config.cbar_width)
        self.cbar_width_spinbox.grid(row=3, column=1, **self.grid_kwargs)
        self.cbar_length_spinbox = CTkSpinbox(self.tab4, from_=0, to=100, increment=5, is_float=True)
        self.cbar_length_spinbox.set(100 * config.cbar_length)
        self.cbar_length_spinbox.grid(row=4, column=1, **self.grid_kwargs)
        self.cbar_pad_spinbox = CTkSpinbox(self.tab4, from_=0, to=500, increment=20)
        self.cbar_pad_spinbox.set(config.cbar_pad)
        self.cbar_pad_spinbox.grid(row=5, column=1, **self.grid_kwargs)
        self.cbar_label_entry = CTkEntry(self.tab4)
        if config.cbar_label is not None:
            self.cbar_label_entry.insert('0', config.cbar_label)
        self.cbar_label_entry.grid(row=6, column=1, **self.grid_kwargs)
        self.cbar_ticks_entry = CTkEntry(self.tab4)
        if config.cbar_ticks is not None:
            self.cbar_ticks_entry.insert('0', ','.join([str(item) for item in config.cbar_ticks]))
        self.cbar_ticks_entry.grid(row=7, column=1, **self.grid_kwargs)
        self.tabview.grid(row=0, column=0, sticky='nsew')


class SliderFrame(CTkFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(1, weight=1, minsize=20)
        self.sliders = {}
        for i, plane in enumerate(PLANES_4D):
            label = CTkLabel(self, text=plane.capitalize())
            label.grid(row=0, column=i, sticky='nsew', padx=15)
            from_to = (0, 400) if plane == 'time' else (-200, 200)
            slider = CTkSlider(self, orientation='vertical', from_=from_to[0], to=from_to[1], height=50)
            slider.set(0)
            slider.grid(row=1, column=i, sticky='ns')
            self.sliders.update({plane: slider})


class PagesFrame(CTkFrame):
    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config')
        width = kwargs.pop('width')
        super().__init__(*args, **kwargs)
        self.grid_columnconfigure((0, 1, 2), weight=1)
        grid_kwargs = {'padx': 1, 'sticky': 'nsew'}
        self.previous_button = CTkButton(self, text='Previous', width=width // 3)
        self.previous_button.grid(row=0, column=0, **grid_kwargs)
        self.page_label = CTkLabel(self, text=f'Page {config.page + 1} of {config.n_pages}', width=width // 3)
        self.page_label.grid(row=0, column=1, **grid_kwargs)
        self.next_button = CTkButton(self, text='Next', width=width // 3)
        self.next_button.grid(row=0, column=2, **grid_kwargs)


class SidebarFrame(CTkFrame):
    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config')
        toplevel = kwargs.pop('toplevel')
        super().__init__(*args, **kwargs)
        self.grid_rowconfigure(3, weight=1)
        grid_kwargs = {'sticky': 'nsew', 'pady': 1}
        if not toplevel:
            self.input_frame = InputFrame(self, config=config)
            self.input_frame.grid(row=0, **grid_kwargs)
        self.clear_mask_button = CTkButton(self, text='Clear masks')
        self.clear_mask_button.grid(row=1, **grid_kwargs)
        self.options_frame = OptionsFrame(self, config=config)
        self.options_frame.grid(row=2, **grid_kwargs)
        self.sliders_frame = SliderFrame(self)
        self.sliders_frame.grid(row=3, **grid_kwargs)
        if not toplevel:
            self.pages_frame = PagesFrame(self, config=config, width=self.sliders_frame._desired_width)
            self.pages_frame.grid(row=4, **grid_kwargs)


class MainFrame(CTkFrame):
    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config')
        toplevel = kwargs.pop('toplevel')
        self.toplevel = toplevel
        self.config = Config.from_dict(CONFIG_DICT) if config is None else config
        super().__init__(*args, **kwargs)

        color_string = self._fg_color[self._CTkAppearanceModeBaseClass__appearance_mode]
        self._bg_color_rgba = tuple([v // 256 for v in self.winfo_rgb(color_string)] + [255])
        self._bg_image = None

        self.grid_columnconfigure(0)
        self.grid_columnconfigure(1, weight=1)

        self.image_frame = CTkFrame(self)
        self.image_frame.grid(row=0, column=1, sticky='nsew')
        self.image_label = CTkLabel(self.image_frame, text='')
        self.image_label.grid(sticky='nsew')

        self.time_dropdown_clicked = time()
        self.fullscreen_height_change = False

        self.niigrid1 = None
        self.niigrid2 = None
        self.load_niigrid()
        self.image = None
        self.image_grid_boxes = None
        self.image_grid_numbers = None
        self.image_overlay = None
        self.image_origin_coords = None
        self.annotation_buttons = []
        self.update_image(hd=True)

        self.sidebar_frame = SidebarFrame(self, config=self.config, toplevel=toplevel)
        self.sidebar_frame.grid(row=0, column=0, sticky='nsew')
        self.menu = self.init_menu_bar()

        self.image_label.bind('<Motion>', self.set_image_overlay)
        self.image_label.bind('<Leave>', lambda event: self.set_image_overlay(event, remove_overlay=True))
        self.image_label.bind('<Button-1>', partial(self.update_origin_click, hd=False))
        self.image_label.bind('<B1-Motion>', partial(self.update_origin_click, hd=False))
        self.image_label.bind('<ButtonRelease-1>', self.update_origin_click)
        if not self.toplevel:
            self.set_input_frame()
        self.sidebar_frame.clear_mask_button.configure(command=self.clear_masks)
        self.add_sliders_commands(self.sidebar_frame.sliders_frame.sliders)
        self.sidebar_frame.options_frame.show_button.configure(command=self.set_options_frame)
        if not toplevel:
            self.sidebar_frame.pages_frame.previous_button.configure(command=self.set_page)
            self.sidebar_frame.pages_frame.next_button.configure(command=partial(self.set_page, next=True))

    def set_scaling(self, scaling):
        scale = scaling / self._CTkScalingBaseClass__widget_scaling
        sidebar_size = [scale * self.sidebar_frame._current_width, scale * self.sidebar_frame._current_height]
        size = [sidebar_size[0] + self.image.size[0], max(200, self.image.size[1])]
        set_widget_scaling(scaling)
        self.master.geometry(f'{int(size[0])}x{int(size[1])}')
        self.time_dropdown_clicked = time()

    def init_menu_bar(self):
        menu = CTkMenuBar(self.master)
        file_cascade = menu.add_cascade('Open')
        file_dropdown = CustomDropdownMenu(widget=file_cascade)
        file_dropdown.add_option(option='Load 3D image...', command=self.open_files)
        template_submenu = file_dropdown.add_submenu('...or template')
        for template in TEMPLATES:
            template_submenu.add_option(template, command=partial(self.open_files, filepaths=[TEMPLATES[template]], dropdown=True))
        file_dropdown.add_separator()
        file_dropdown.add_option(option='Load 3D mask...', command=self.open_files)
        atlas_submenu = file_dropdown.add_submenu('...or atlas')
        for atlas in ATLASES:
            atlas_submenu.add_option(atlas, command=partial(self.open_files, filepaths=[ATLASES[atlas]], is_mask=True, dropdown=True))
        file_dropdown.add_separator()
        file_dropdown.add_option(option='Load configuration', command=self.load_config)

        save_cascade = menu.add_cascade('Save')
        save_dropdown = CustomDropdownMenu(widget=save_cascade)
        save_image_submenu = save_dropdown.add_submenu('Save image as')
        for ftype in FILETYPES:
            save_image_submenu.add_option(ftype[1], command=partial(self.save_image, ftype))
        save_dropdown.add_option('Save all images', command=self.save_all_images_or_gifs)
        save_dropdown.add_option('Save GIF', command=self.save_gif)
        save_dropdown.add_option('Save all GIFs', command=partial(self.save_all_images_or_gifs, gif=True))
        save_dropdown.add_option('Save annotations', command=self.save_annotations)
        save_dropdown.add_option('Save configuration', command=self.save_config)

        appearance_cascade = menu.add_cascade('Appearance')
        appearance_dropdown = CustomDropdownMenu(widget=appearance_cascade)
        appearance_dropdown.add_option('Dark mode', command=partial(set_appearance_mode, mode_string='dark'))
        appearance_dropdown.add_option('Light mode', command=partial(set_appearance_mode, mode_string='light'))
        appearance_dropdown.add_separator()
        scaling_submenu = appearance_dropdown.add_submenu('Widget scaling')
        for scaling in SCALINGS:
            label = f'{int(100 * scaling)}%'
            scaling_submenu.add_option(label, command=partial(self.set_scaling, scaling))
        tmp_height_submenu = appearance_dropdown.add_submenu('Temp. image height')
        for tmp_height in [None, *TMP_HEIGHTS]:
            label = 'Disable (can be laggy)' if tmp_height is None else tmp_height
            tmp_height_submenu.add_option(label, command=partial(self.update_config, attribute='tmp_height', event=tmp_height))
        appearance_dropdown.add_separator()
        appearance_dropdown.add_option(option='Fullscreen', command=partial(set_fullscreen, app=self))

        extra_options_cascade = menu.add_cascade('Extra Options')
        extra_options_dropdown = CustomDropdownMenu(widget=extra_options_cascade)
        extra_options_dropdown.add_option(option='Annotations', command=self.set_annotation_buttons)
        linewidth_submenu = extra_options_dropdown.add_submenu('Linewidth')
        for linewidth in list(range(1, 9)):
            linewidth_submenu.add_option(option=linewidth, command=partial(self.update_config, attribute='linewidth', event=linewidth))
        linecolor_submenu = extra_options_dropdown.add_submenu('Linecolor')
        for linecolor in LINECOLORS:
            linecolor_submenu.add_option(option=linecolor, command=partial(self.update_config, attribute='linecolor', event=linecolor))
        padcolor_submenu = extra_options_dropdown.add_submenu('Padcolor')
        for padcolor in PADCOLORS:
            padcolor_submenu.add_option(option=padcolor, command=partial(self.update_config, attribute='cbar_pad_color', event=padcolor))
        nrows_submenu = extra_options_dropdown.add_submenu('Number of rows')
        for nrows in [None] + list(range(1, 9)):
            option = 'Auto' if nrows is None else str(nrows)
            nrows_submenu.add_option(option=option, command=partial(self.update_config, attribute='nrows', event=nrows))
        glass_mode_submenu = extra_options_dropdown.add_submenu('Glassbrain mode')
        for glass_mode in [None] + list(GLASS_MODES):
            glass_mode_submenu.add_option(option=glass_mode, command=partial(self.update_config, attribute='glass_mode', event=glass_mode))
        coord_sys_submenu = extra_options_dropdown.add_submenu('Coordinate system')
        for coord_sys in COORDINATE_SYSTEMS:
            coord_sys_submenu.add_option(option=coord_sys, command=partial(self.update_config, attribute='coord_sys', event=coord_sys))
        extra_options_dropdown.add_option(option='Squeeze', command=partial(self.update_config, attribute='squeeze', switch=True))

        menu.add_cascade('Help', postcommand=partial(open_new_tab, TUTORIAL_URL))

        about_cascade = menu.add_cascade('About')
        about_dropdown = CustomDropdownMenu(widget=about_cascade)
        about_dropdown.add_option(option='Homepage', command=partial(self.open_url, HOMEPAGE_URL))
        about_dropdown.add_option(option='Author', command=partial(self.open_url, AUTHOR_URL))
        about_dropdown.add_separator()
        about_dropdown.add_option(option=f'App-Version {__version__}', command=partial(self.open_url, RELEASE_URL))
        return menu

    def open_url(self, url):
        self.time_dropdown_clicked = time()
        open_new_tab(url)

    def set_input_frame(self, event=None):
        frame = self.sidebar_frame.input_frame
        frame.view_button.configure(command=self.set_view)
        frame.image_entry.bind('<Return>', lambda e: self.open_files(filepaths=frame.image_entry.get()))
        frame.image_entry.dnd_bind('<<Drop>>', self.open_files)
        frame.mask_entry.bind('<Return>', lambda e: self.open_files(filepaths=frame.mask_entry.get(), is_mask=True))
        frame.mask_entry.bind('<Control-Alt-n>', lambda e: self.convert_dicom_and_open(input_filepath=frame.image_entry.get(),
                                                                                       output_dirpath=frame.mask_entry.get()))
        frame.mask_entry.dnd_bind('<<Drop>>', partial(self.open_files, is_mask=True))

    def set_options_frame(self, event=None):
        frame = self.sidebar_frame.options_frame
        frame.show(self.config)
        # TAB: MAIN
        frame.layout_entry.bind('<Return>', lambda e: self.update_config('layout', frame.layout_entry.get()))
        frame.layout_options.configure(command=lambda e: self.set_layout(e, frame.layout_entry))
        frame.cmap_entry.bind('<Return>', lambda e: self.update_config('cmap', frame.cmap_entry.get()))
        frame.cmap_options.configure(command=lambda e: self.set_cmap(e, frame.cmap_entry))
        frame.cmap_mask_entry.bind('<Return>', lambda e: self.update_config('cmap', frame.cmap_mask_entry.get(), is_mask=True))
        frame.cmap_mask_options.configure(command=lambda e: self.set_cmap(e, frame.cmap_mask_entry, is_mask=True))
        frame.height_spinbox.configure(command=lambda e: self.set_height(e))
        frame.max_samples_spinbox.configure(command=self.set_max_samples)
        # TAB: IMAGE
        frame.equal_hist_checkbox.configure(command=partial(self.update_config, attribute='equal_hist', switch=True))
        frame.qrange_start_spinbox.configure(command=self.set_quantile_range)
        frame.qrange_stop_spinbox.configure(command=lambda e: self.set_quantile_range(e, stop=True))
        frame.vrange_start_spinbox.configure(command=lambda e: self.set_value_range(e))
        frame.vrange_stop_spinbox.configure(command=lambda e: self.set_value_range(e, stop=True))
        frame.transp_if_entry.bind('<Return>', self.set_transp_if)
        frame.resizing_options.configure(command=lambda e: self.update_config('resizing', RESIZINGS.index(e)))
        # TAB: MASK
        frame.alpha_spinbox.configure(command=lambda e: self.update_config('alpha', e / 100))
        frame.qrange_start_mask_spinbox.configure(command=lambda e: self.set_quantile_range(e, is_mask=True))
        frame.qrange_stop_mask_spinbox.configure(command=lambda e: self.set_quantile_range(e, is_mask=True, stop=True))
        frame.vrange_start_mask_spinbox.configure(command=lambda e: self.set_value_range(e, is_mask=True))
        frame.vrange_stop_mask_spinbox.configure(command=lambda e: self.set_value_range(e, stop=True, is_mask=True))
        frame.transp_if_mask_entry.bind('<Return>', partial(self.set_transp_if, is_mask=True))
        frame.resizing_mask_options.configure(command=lambda e: self.update_config('resizing', RESIZINGS.index(e), is_mask=True))
        frame.is_atlas_checkbox.configure(command=self.set_is_atlas)
        # TAB: OVERLAY
        frame.crosshair_checkbox.configure(command=partial(self.update_config, attribute='crosshair', switch=True))
        frame.coordinates_checkbox.configure(command=partial(self.update_config, attribute='coordinates', switch=True))
        frame.header_checkbox.configure(command=partial(self.update_config, attribute='header', switch=True))
        frame.histogram_checkbox.configure(command=partial(self.update_config, attribute='histogram', switch=True))
        frame.fpath_spinbox.configure(command=lambda e: self.update_config('fpath', e))
        frame.title_entry.bind('<Return>', self.set_title)
        frame.fontsize_spinbox.configure(command=lambda e: self.update_config('fontsize', e))
        # TAB: COLORBAR
        frame.cbar_options.configure(command=self.set_cbar)
        frame.cbar_x_spinbox.configure(command=lambda e: self.update_config('cbar_x', e / 100))
        frame.cbar_y_spinbox.configure(command=lambda e: self.update_config('cbar_y', e / 100))
        frame.cbar_width_spinbox.configure(command=lambda e: self.update_config('cbar_width', e / 100))
        frame.cbar_length_spinbox.configure(command=lambda e: self.update_config('cbar_length', e / 100))
        frame.cbar_pad_spinbox.configure(command=lambda e: self.update_config('cbar_pad', e))
        frame.cbar_label_entry.bind('<Return>', lambda e: self.update_config('cbar_label', e.widget.get()))
        frame.cbar_ticks_entry.bind('<Return>', self.set_cbar_ticks)

    @property
    def niigrid(self):
        return [self.niigrid1, self.niigrid2][self.config.view - 1]

    def load_niigrid(self):
        setattr(self, f'niigrid{self.config.view}', NiftiImageGrid(self.config.get_filepaths()))

    def set_view(self, event):
        self.config.view = int(event[-1])
        if getattr(self, f'niigrid{self.config.view}') is None:
            self.load_niigrid()
        self.update_image()

    def clear_masks(self):
        self.config.remove_mask_layers()
        self.load_niigrid()
        self.update_image()

    def add_sliders_commands(self, sliders):
        for i, plane in enumerate(PLANES_4D):
            sliders[plane].bind('<Button-4>', partial(self.update_origin, plane=plane, scroll_speed=1))
            sliders[plane].bind('<Button-5>', partial(self.update_origin, plane=plane, scroll_up=False, scroll_speed=1))
            sliders[plane].configure(command=partial(self.update_origin, plane=plane, hd=False))
            sliders[plane].bind('<ButtonRelease-1>', self.update_image)

    def set_layout(self, event, entry):
        entry.insert(0, LAYOUT_STRINGS[event])
        entry.delete(len(LAYOUT_STRINGS[event]), 'end')
        self.update_config('layout', event)

    def set_max_samples(self, max_samples):
        self.config.set_max_samples(max_samples)
        self.load_niigrid()
        self.update_image()

    def set_annotation_buttons(self):
        self.config.annotations = ~self.config.annotations
        if len(self.annotation_buttons) > 0:
            self.destroy_annotation_buttons()
        else:
            self.create_annotation_buttons()

    def destroy_annotation_buttons(self):
        if len(self.annotation_buttons) > 0:
            for i in range(len(self.annotation_buttons)):
                self.annotation_buttons[i].destroy()
            self.annotation_buttons = []

    def create_annotation_buttons(self, annotations_=('0', '1', '2')):
        self.annotation_buttons = []
        scaling = self._CTkScalingBaseClass__widget_scaling
        for nimage, box in zip(self.niigrid1.niis, self.image_grid_boxes):
            button = CTkSegmentedButton(self.image_frame, values=annotations_,
                                        command=partial(self.set_annotation, filepath=nimage.nics[0].filepath))
            button.set(annotations_[0])
            button.place(x=int(round(box[2] / scaling)), y=int(round(box[1] / scaling)), anchor='ne')
            self.annotation_buttons.append(button)

    def set_annotation(self, event, filepath):
        self.config.annotation_dict.update({filepath: int(event)})

    def set_cmap(self, event, entry, is_mask=False):
        if event == 'CATALOG':
            open_new_tab('https://cmap-docs.readthedocs.io/en/latest/catalog/')
        else:
            entry.insert(0, event)
            entry.delete(len(event), 'end')
            self.update_config('cmap', event, is_mask)

    def set_height(self, height):
        if self.master.is_fullscreen:
            self.update_config('height', height)
        else:
            width = self.image.size[0] * height / self.image.size[1]
            width += self.sidebar_frame._current_width * self._CTkScalingBaseClass__widget_scaling
            menubar_height = self._CTkScalingBaseClass__widget_scaling * self.menu._current_height
            self.master.geometry(f'{int(width)+1}x{height + int(menubar_height)+1}')

    def set_title(self, event):
        self.config.set_title(event.widget.get())
        self.update_image()

    def unset_title(self):
        if hasattr(self.sidebar_frame.options_frame, 'title_entry'):
            self.sidebar_frame.options_frame.title_entry.delete(0, 'end')
        self.config.set_title('')
        self.update_image()

    def set_equal_hist(self, event=None):
        if hasattr(self.sidebar_frame.options_frame, 'equal_hist_checkbox'):
            self.sidebar_frame.options_frame.equal_hist_checkbox.toggle()
        else:
            self.update_config('equal_hist', switch=True)

    def set_transp_if(self, event=None, is_mask=False):
        substr = '_mask' if is_mask else ''
        transp_if = getattr(self.sidebar_frame.options_frame, f'transp_if{substr}_entry').get()
        transp_if = None if transp_if == '' else transp_if
        self.update_config('transp_if', transp_if, is_mask=is_mask)

    def set_quantile_range(self, event, is_mask=False, stop=False, increment=None):
        if self.config.qrange[-1 if is_mask else 0] is None:
            qrange = list(QRANGE[int(is_mask)])
        else:
            qrange = list(self.config.qrange[-1 if is_mask else 0])
        qrange[int(stop)] = event / 100 if increment is None else qrange[int(stop)] + increment / 100
        qrange[int(stop)] = min(max(0, qrange[int(stop)]), 1)
        self.update_config('qrange', qrange, is_mask)
        value_range = self.niigrid.niis[0].cmaps[-1 if is_mask else 0].vrange
        self.config.set_layer_attribute('vrange', None, is_mask)  # Setting vrange to None such that qrange has effect
        if hasattr(self.sidebar_frame.options_frame, 'qrange_start_spinbox'):
            if is_mask:
                self.sidebar_frame.options_frame.vrange_start_mask_spinbox.set(value_range[0])
                self.sidebar_frame.options_frame.vrange_stop_mask_spinbox.set(value_range[-1])
                if increment is not None:
                    self.sidebar_frame.options_frame.qrange_start_mask_spinbox.set(qrange[0] * 100)
                    self.sidebar_frame.options_frame.qrange_stop_mask_spinbox.set(qrange[1] * 100)
            else:
                self.sidebar_frame.options_frame.vrange_start_spinbox.set(value_range[0])
                self.sidebar_frame.options_frame.vrange_stop_spinbox.set(value_range[-1])
                if increment is not None:
                    self.sidebar_frame.options_frame.qrange_start_spinbox.set(qrange[0] * 100)
                    self.sidebar_frame.options_frame.qrange_stop_spinbox.set(qrange[1] * 100)

    def set_value_range(self, event, is_mask=False, stop=False):
        vrange = self.niigrid.niis[0].cmaps[-1 if is_mask else 0].vrange
        vrange[-1 if stop else 0] = event
        self.update_config('vrange', vrange, is_mask)

    def set_is_atlas(self):
        self.update_config('is_atlas', not self.config.is_atlas[-1], is_mask=True)

    def set_cbar(self, event):
        self.config.cbar_vertical = event == 'vertical'
        self.update_config('cbar', event != '')

    def set_cbar_ticks(self, event):
        self.config.set_cbar_ticks(event.widget.get())
        self.update_image()

    def set_page(self, next=False):
        page = self.config.page + 1 if next else self.config.page - 1
        if page in list(range(self.config.n_pages)):
            self.config.page = page
            self.load_niigrid()
            self.update_image()
            self.sidebar_frame.pages_frame.page_label.configure(text=f'Page {page + 1} of {self.config.n_pages}')

    def update_config(self, attribute, event=None, is_mask=False, switch=False):
        if attribute in LAYER_ATTRIBUTES:
            self.config.set_layer_attribute(attribute, event, is_mask)
        else:
            setattr(self.config, attribute, not getattr(self.config, attribute) if switch else event)
        self.update_image()
        self.focus_set()
        if attribute in MENUBAR_ATTRIBUTES:
            self.time_dropdown_clicked = time()

    def convert_dicom_and_open(self, input_filepath=None, output_dirpath=None):
        filepaths = dcm2nii(input_filepath, output_dirpath)
        if len(filepaths) > 0:
            image_path, mask_path = f'{output_dirpath}/*.ni*', ''
            self.sidebar_frame.input_frame.image_entry.insert('0', image_path)
            self.sidebar_frame.input_frame.image_entry.delete(len(image_path), 'end')
            self.sidebar_frame.input_frame.mask_entry.insert('0', mask_path)
            self.sidebar_frame.input_frame.mask_entry.delete(len(mask_path), 'end')
            self.open_files(filepaths=filepaths)

    def open_files(self, event=None, filepaths=None, is_mask=False, title='Open Nifti Files', dropdown=False):
        if filepaths is None:
            if isinstance(event, TkinterDnD.DnDEvent):
                filepaths = parse_dnd_filepaths(event.data)
            else:
                filepaths = filedialog.askopenfilenames(title=title, filetypes=[('All Files', '*.*')])
        if filepaths:
            self.unset_title()
            self.config.add_filepaths(filepaths, is_mask)
            self.load_niigrid()
            self.update_image()
            self.focus_set()
            if dropdown:
                self.time_dropdown_clicked = time()

    def remove_mask_layers(self):
        self.config.remove_mask_layers()
        setattr(self, f'niigrid{self.config.view}', NiftiImageGrid(self.config.get_filepaths()))
        self.update_image()

    def update_origin(self, value, plane, scroll_up=True, scroll_speed=0, hd=True):
        if scroll_speed:
            value = self.config.origin[PLANES_4D.index(plane)] + (1 if scroll_up else -1) * scroll_speed
            self.sidebar_frame.sliders_frame.sliders[plane].set(value)
        self.config.origin[PLANES_4D.index(plane)] = value
        self.update_image(hd)

    def update_image(self, hd=True):
        self.image = self.get_image(hd)
        self.update_overlay_and_annotations()
        if len(self.image.mode) > 1:
            self.image = Image.alpha_composite(self._bg_image, self.image)
        filterwarnings('ignore', category=UserWarning)
        self.image_label.configure(image=ImageTk.PhotoImage(self.image, size=self.image.size))
        filterwarnings('default', category=UserWarning)
        if hasattr(self, 'sidebar_frame'):
            self.update_sidebar()

    def get_image(self, hd=True):
        config_dict = self.config.to_dict(grid_kwargs_only=True)
        if hd:
            config_dict.update({'tmp_height': None})
        return self.niigrid.get_image(**config_dict)

    def update_overlay_and_annotations(self):
        updated_grid_boxes = self.niigrid.boxes
        if self.image_grid_boxes is None or updated_grid_boxes != self.image_grid_boxes:
            self._bg_image = Image.new('RGBA', self.image.size, self._bg_color_rgba)
            self.image_grid_boxes = updated_grid_boxes
            self.image_grid_numbers = self.get_grid_numbers()
            self.image_origin_coords = self.get_origin_coordinates()
            if self.config.annotations:
                self.destroy_annotation_buttons()
                self.create_annotation_buttons()

    def update_sidebar(self):
        if hasattr(self.sidebar_frame.options_frame, 'tabview'):
            frame = self.sidebar_frame
            nimage = self.niigrid.niis[0]
            frame.options_frame.vrange_start_spinbox.set(nimage.cmaps[0].vrange[0])
            frame.options_frame.vrange_stop_spinbox.set(nimage.cmaps[0].vrange[-1])
            frame.options_frame.resizing_options.set(RESIZINGS[self.config.resizing[0]])
            frame.options_frame.resizing_mask_options.set(RESIZINGS[self.config.resizing[-1]])
            if self.config.n_layers > 1:
                frame.options_frame.vrange_start_mask_spinbox.set(nimage.cmaps[-1].vrange[0])
                frame.options_frame.vrange_stop_mask_spinbox.set(nimage.cmaps[-1].vrange[-1])
        if hasattr(self.sidebar_frame, 'pages_frame'):
            page = min(self.config.page, self.config.n_pages - 1)
            self.sidebar_frame.pages_frame.page_label.configure(text=f'Page {page + 1} of {self.config.n_pages}')

    def set_image_overlay(self, event, remove_overlay=False):
        tk_image = ImageTk.PhotoImage(self.image, size=self.image.size)
        if not remove_overlay and 0 <= event.x < self.image.size[0] and 0 <= event.y < self.image.size[1]:
            box_number = self.image_grid_numbers[event.x, event.y]
            if 0 <= box_number < len(self.image_grid_boxes) and len(self.image_grid_boxes) > 1:
                box = self.image_grid_boxes[box_number]
                box_frame = Image.fromarray(get_window_frame(size=(box[2] - box[0], box[3] - box[1])))
                alpha = Image.new('L', self.image.size, 255)
                alpha.paste(box_frame, self.image_grid_boxes[box_number])
                im = Image.composite(self.image, Image.new(self.image.mode, self.image.size, 'white'), alpha)
                tk_image = ImageTk.PhotoImage(im, size=self.image.size)
        filterwarnings('ignore', category=UserWarning)
        self.image_label.configure(image=tk_image)
        filterwarnings('default', category=UserWarning)

    def get_grid_numbers(self):
        numbers = -np.ones(self.image.size, dtype=np.int16)
        for i, box in enumerate(self.image_grid_boxes):
            numbers[box[0]:box[2], box[1]:box[3]] = i
        return numbers

    def update_origin_click(self, event, hd=True, menubar_wait=.5):
        time_since_menubar = time() - self.time_dropdown_clicked
        if 0 <= event.x < self.image.size[0] and 0 <= event.y < self.image.size[1] and time_since_menubar > menubar_wait:
            origin = np.append(self.image_origin_coords[event.x, event.y], self.config.origin[3])
            plane_idx = np.isnan(origin).argmax()
            origin[plane_idx] = self.config.origin[plane_idx]
            self.config.origin = origin.tolist()
            self.update_image(hd)
            for plane, v in zip(PLANES, origin):
                self.sidebar_frame.sliders_frame.sliders[plane].set(v)

    def get_origin_coordinates(self):
        coords = np.zeros((*self.image.size, 3), dtype=np.float32)
        for nii, grid_box in zip(self.niigrid.niis, self.niigrid.boxes):
            bounds = nii.nics[0].get_origin_bounds(self.config.coord_sys)
            for i, kw in enumerate(nii.nics[0]._image_props):
                size = kw['size']
                dim = PLANES.index(kw['plane'])
                x, y = [ii for ii in range(3) if ii != dim]
                box_coords = np.meshgrid(*[np.linspace(bounds[0, x], bounds[1, x], size[0]),
                                           np.linspace(bounds[1, y], bounds[0, y], size[1])], indexing='ij', copy=False)
                box_coords = np.stack(box_coords, axis=-1)
                box_coords = np.insert(box_coords, dim, np.nan, axis=-1)
                box = grid_box[0] + kw['box'][0], grid_box[1] + kw['box'][1]
                coords[box[0]:box[0] + size[0], box[1]:box[1] + size[1]] = box_coords
        return coords

    def save_image(self, filetype):
        extension = filetype[1].split(';')[0][1:]
        filepath = filedialog.asksaveasfilename(defaultextension=extension, filetypes=[filetype])
        if filepath:
            config_dict = self.config.to_dict(grid_kwargs_only=True)
            if extension in ['.png', '.jpg', '.jpeg', '.tif', '.tiff']:
                image = self.niigrid.get_image(**config_dict)
                image.save(filepath)
            else:
                config_dict.pop('tmp_height')
                self.niigrid.save_image(filepath, **config_dict)

    def save_gif(self):
        filepath = filedialog.asksaveasfilename(defaultextension='.gif',
                                                filetypes=[('Graphics Interchange Format', '*.gif')])
        if filepath:
            config_dict = self.config.to_dict(grid_kwargs_only=True)
            save_gif(self.niigrid, filepath, duration=50, loop=0, start=None, stop=None, **config_dict)

    def save_all_images_or_gifs(self, gif=False):
        dirpath = filedialog.askdirectory()
        if dirpath:
            config_dict = self.config.to_dict(grid_kwargs_only=True)
            save_images_or_gifs(self.config.filepaths, dirpath, gif, self.config.max_samples, **config_dict)

    def save_config(self):
        filepath = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON Files', '.json')])
        if filepath:
            self.config.save(filepath)

    def load_config(self):
        filepath = filedialog.askopenfilename(title='Open Config File', filetypes=[('JSON Files', '.json')])
        if filepath:
           self.config = Config.from_json(filepath)
           self.load_niigrid()
           self.update_image()

    def save_annotations(self):
        filepath = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('Comma-separated values', '.csv')])
        if filepath:
            self.config.save_annotations(filepath)


class ToplevelWindow(CTkToplevel):
    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config')
        super().__init__(*args, **kwargs)
        self.title('NiftiView')
        set_icon(self)
        self.is_fullscreen = False
        self.mainframe = MainFrame(self, config=config, toplevel=True)
        self.mainframe.pack(anchor='nw', fill='both', expand=True)
        add_key_bindings(self)


class NiftiView(CTk):
    def __init__(self, config=None):
        super().__init__()
        self.title('NiftiView')
        set_icon(self)
        self.is_fullscreen = False
        self.mainframe = MainFrame(self, config=config, toplevel=False)
        self.mainframe.pack(anchor='nw', fill='both', expand=True)
        self.toplevel_window = None
        self.mainframe.image_label.bind('<Double-Button-1>', self.set_toplevel_window)
        self.bind(f'<Shift-BackSpace>', lambda e: self.mainframe.set_page(next=False))
        self.bind(f'<Button-3>', lambda e: self.mainframe.set_page(next=True))
        add_key_bindings(self)

    def set_toplevel_window(self, event):
        if self.toplevel_window is not None:
            self.toplevel_window.destroy()
        if 0 <= event.x < self.mainframe.image.size[0] and 0 <= event.y < self.mainframe.image.size[1]:
            window_number = self.mainframe.image_grid_numbers[event.x, event.y]
            config = deepcopy(self.mainframe.config)
            fpaths = config.get_filepaths()
            if 0 <= window_number < len(fpaths):
                setattr(config, f'filepaths_view{config.view}', [fpaths[window_number]])
                self.toplevel_window = ToplevelWindow(self, config=config)


def add_key_bindings(app):
    app.bind('<A>', lambda e: app.mainframe.set_quantile_range(None, increment=-5))
    app.bind('<D>', lambda e: app.mainframe.set_quantile_range(None, increment=5))
    app.bind('<S>', lambda e: app.mainframe.set_quantile_range(None, increment=-1, stop=True))
    app.bind('<W>', lambda e: app.mainframe.set_quantile_range(None, increment=1, stop=True))
    app.bind('<Shift-Return>', lambda e: app.mainframe.set_equal_hist())
    app.bind('<Escape>', lambda e: app.wm_attributes('-fullscreen', False))
    app.bind('<Configure>', debounce(app, partial(resize_window, app)))
    app.bind('<Shift-space>', lambda e: app.mainframe.update_config('alpha', 0.))
    app.bind('<Shift-KeyRelease-space>', lambda e: app.mainframe.update_config('alpha', app.mainframe.sidebar_frame.options_frame.alpha_spinbox.get() / 100))
    for plane, keys in zip(PLANES_4D, [('Left', 'Right'), ('Shift-Left', 'Shift-Right'), ('Down', 'Up'), ('Shift-Down', 'Shift-Up')]):
        app.bind(f'<{keys[0]}>', partial(app.mainframe.update_origin, plane=plane, scroll_up=False, scroll_speed=1))
        app.bind(f'<{keys[1]}>', partial(app.mainframe.update_origin, plane=plane, scroll_speed=1))


def resize_window(app, *args):
    if str(args[0]._w) in ['.', '.!toplevelwindow']:
        if not app.is_fullscreen:
            size = [app.mainframe._current_width - app.mainframe.sidebar_frame._current_width, app.mainframe._current_height]
            ratio = size[0] / size[1]
            scaling = float(app.mainframe._CTkScalingBaseClass__widget_scaling)
            size = [int(round(size[0] * scaling)), int(round(size[1] * scaling))]
            image_ratio = app.mainframe.image.size[0] / app.mainframe.image.size[1]
            height = int(size[1] if ratio >= image_ratio else size[0] / image_ratio)
            if height > 0 and abs(height - app.mainframe.image.size[1]) > 1:
                app.mainframe.config.height = int(height)
                app.mainframe.update_image(hd=True)
                if hasattr(app.mainframe.sidebar_frame.options_frame, 'height_spinbox'):
                    app.mainframe.sidebar_frame.options_frame.height_spinbox.set(height)
                #app.after(30, app.mainframe.update_image(hd=True))
        app.is_fullscreen = window_is_fullscreen_or_maximized(app)


def window_is_fullscreen_or_maximized(app):
    return app.attributes('-fullscreen') or app.winfo_height() > app.winfo_screenheight() - 100


def set_icon(app):
    app.iconpath = ImageTk.PhotoImage(file=f'{DATA_PATH}/niftiview.ico')
    app.wm_iconbitmap()
    app.iconphoto(False, app.iconpath)


def main(filepaths=None):
    config = Config.from_dict(CONFIG_DICT)
    if len(argv) > 1:
        config.add_filepaths(filepaths)
    if config.scaling is not None:
        set_widget_scaling(config.scaling)
    if config.appearance_mode is not None:
        set_appearance_mode(config.appearance_mode)
    app = NiftiView(config)
    app.mainloop()


if __name__ == '__main__':
    main(filepaths=argv[1:] if len(argv) > 1 else None)
