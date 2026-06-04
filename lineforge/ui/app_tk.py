import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import customtkinter as ctk
import threading

from ..settings import Settings
from ..utils import list_images
from ..pipeline import run_all, cancel_pipeline, PipelineResult
from .theme import get_theme_path
from ..deps import find_vpipe

LOG_FILENAME_PATTERN = re.compile(r'\[\d+/\d+\]\s*(.+\.(png|jpg|jpeg|svg|pdf|eps))')


class LabeledSlider(ctk.CTkFrame):
    def __init__(self, master, label_text, from_, to, variable, resolution=1, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.var = variable
        self.label_text = label_text
        self.resolution = resolution

        self.grid_columnconfigure(1, weight=1)

        self.lbl_name = ctk.CTkLabel(self, text=label_text, anchor="w", width=120)
        self.lbl_name.grid(row=0, column=0, padx=(0, 10), sticky="w")

        # Calculate number of steps based on resolution
        steps = None
        if resolution and resolution > 0:
            steps = int(round((to - from_) / resolution))

        self.slider = ctk.CTkSlider(
            self,
            from_=from_,
            to=to,
            number_of_steps=steps,
            variable=variable,
            command=self._on_slider_move,
            button_color=("#9dacbb", "#7d8c9b"),
            button_hover_color=("#8ca0b5", "#5c6d80"),
            progress_color=("#9dacbb", "#7d8c9b")
        )
        self.slider.grid(row=0, column=1, sticky="ew")

        self.lbl_val = ctk.CTkLabel(self, text="", width=50, anchor="e")
        self.lbl_val.grid(row=0, column=2, padx=(10, 0), sticky="e")

        self._update_val_label(variable.get())

        # Trace variable to update display when it changes programmatically
        self.var.trace_add("write", lambda *args: self._update_val_label(self.var.get()))

    def _on_slider_move(self, val):
        if isinstance(self.var, tk.IntVar) or self.resolution >= 1:
            val = int(round(val))
        else:
            val = round(val, 2)
        self.var.set(val)
        self._update_val_label(val)

    def _update_val_label(self, val):
        try:
            if isinstance(self.var, tk.IntVar) or self.resolution >= 1:
                self.lbl_val.configure(text=str(int(round(val))))
            else:
                self.lbl_val.configure(text=f"{float(val):.1f}")
        except Exception:
            pass

    def configure_state(self, state):
        self.slider.configure(state=state)
        if state == "disabled":
            self.lbl_name.configure(text_color="#9b9b9b")
            self.lbl_val.configure(text_color="#9b9b9b")
        else:
            default_color = ctk.ThemeManager.theme.get('CTkLabel', {}).get('text_color', ("black", "white"))
            self.lbl_name.configure(text_color=default_color)
            self.lbl_val.configure(text_color=default_color)


class CardFrame(ctk.CTkFrame):
    def __init__(self, master, title, enable_var=None, enable_callback=None, header_fg_color=None, **kwargs):
        super().__init__(master, corner_radius=12, border_width=1, border_color="#9b9b9b", **kwargs)
        self.title = title
        self.enable_var = enable_var
        self.enable_callback = enable_callback

        self.grid_columnconfigure(0, weight=1)

        # Header Frame with colored background
        if header_fg_color is None:
            header_fg_color = ("gray90", "gray20")
        
        self.header_frame = ctk.CTkFrame(self, fg_color=header_fg_color, corner_radius=10, height=40)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        self.header_frame.grid_columnconfigure(0, weight=1)

        # Title Label (Bold, slightly larger)
        is_custom_header = (header_fg_color != ("gray90", "gray20"))
        self.lbl_title = ctk.CTkLabel(
            self.header_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white" if is_custom_header else None,
            anchor="w"
        )
        self.lbl_title.grid(row=0, column=0, padx=12, pady=6, sticky="w")

        # Content Frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(10, 12))
        self.grid_rowconfigure(1, weight=1)

        # Toggleable Checkbox in Header
        self.chk_enable = None
        if enable_var is not None:
            self.chk_enable = ctk.CTkCheckBox(
                self.header_frame,
                text="Enable",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white" if is_custom_header else None,
                variable=enable_var,
                command=self._on_enable_toggle,
                width=80
            )
            self.chk_enable.grid(row=0, column=1, padx=12, pady=6, sticky="e")

    def _on_enable_toggle(self):
        enabled = self.enable_var.get()
        self.set_enabled(enabled)
        if self.enable_callback:
            self.enable_callback()

    def set_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"

        def _set_state(parent):
            for child in parent.winfo_children():
                if hasattr(child, "configure_state"):
                    child.configure_state(state)
                    # Don't recurse into custom widgets that manage their own state
                    continue
                elif isinstance(child, (ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkRadioButton, ctk.CTkEntry, ctk.CTkSlider, ctk.CTkOptionMenu, ctk.CTkComboBox, ctk.CTkTextbox)):
                    child.configure(state=state)
                elif isinstance(child, ctk.CTkLabel):
                    if enabled:
                        default_color = ctk.ThemeManager.theme.get('CTkLabel', {}).get('text_color', ("black", "white"))
                        child.configure(text_color=default_color)
                    else:
                        child.configure(text_color="#9b9b9b")
                if isinstance(child, ctk.CTkFrame):
                    _set_state(child)

        _set_state(self.content_frame)

    def update_widgets_state(self):
        if self.chk_enable:
            self._on_enable_toggle()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LineForge")
        self.geometry("1024x700")
        self.minsize(900, 600)

        self.s = Settings.load()
        ctk.set_appearance_mode(self.s.theme)
        ctk.set_default_color_theme(get_theme_path())

        self._log_fh = None
        self._log_path = None
        self._cancel_event = threading.Event()
        self._total_files = 0
        self._current_file = 0
        self._result: PipelineResult | None = None

        self._build_ui()
        self.start_new_log_session()

        self._check_dependencies()
        self._load_recent_inputs()
        self.on_input_path_changed()
        self.refresh_found_count()
        self.card_a.update_widgets_state()
        self.card_b.update_widgets_state()
        self.card_c.update_widgets_state()
        self.card_d.update_widgets_state()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._setup_keyboard_shortcuts()

    def _build_ui(self):
        # --- TOP FRAME (Paths & General) ---
        top = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color="#9b9b9b")
        top.pack(fill="x", padx=10, pady=10)
        top.grid_columnconfigure(1, weight=1)

        # Input Path
        lbl_in = ctk.CTkLabel(top, text="Input (file or folder)", font=ctk.CTkFont(weight="bold"))
        lbl_in.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        default_in = self.s.input_path if self.s.input_path else str(Path.cwd())
        self.v_in_path = tk.StringVar(value=default_in)
        self.e_in = ctk.CTkEntry(top, textvariable=self.v_in_path, border_color="#9b9b9b")
        self.e_in.grid(row=0, column=1, padx=6, pady=10, sticky="we")
        self.v_in_path.trace_add("write", self.on_input_path_changed)

        self.btn_browse_in_file = ctk.CTkButton(
            top, 
            text="Browse File", 
            width=100, 
            command=self.browse_input_file,
            fg_color=("#968596", "#736473"),
            hover_color=("#ab9bab", "#5c4f5c"),
            text_color="white"
        )
        self.btn_browse_in_file.grid(row=0, column=2, padx=(0, 6), pady=10)

        self.btn_browse_in_folder = ctk.CTkButton(
            top, 
            text="Browse Folder", 
            width=110, 
            command=self.browse_input_folder,
            fg_color=("#968596", "#736473"),
            hover_color=("#ab9bab", "#5c4f5c"),
            text_color="white"
        )
        self.btn_browse_in_folder.grid(row=0, column=3, padx=(0, 12), pady=10)

        # Output Path
        lbl_out = ctk.CTkLabel(top, text="Output folder", font=ctk.CTkFont(weight="bold"))
        lbl_out.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")

        default_out = self.s.output_path if self.s.output_path else str(Path.cwd() / "output")
        self.v_out_path = tk.StringVar(value=default_out)
        self.e_out = ctk.CTkEntry(top, textvariable=self.v_out_path, border_color=("#968596", "#736473"))
        self.e_out.grid(row=1, column=1, padx=6, pady=(0, 10), sticky="we")

        self.btn_browse_out = ctk.CTkButton(
            top, 
            text="Browse", 
            width=100, 
            command=self.browse_output_folder,
            fg_color=("#968596", "#736473"),
            hover_color=("#ab9bab", "#5c4f5c"),
            text_color="white"
        )
        self.btn_browse_out.grid(row=1, column=2, columnspan=2, padx=(0, 12), pady=(0, 10), sticky="we")

        # Options Row
        options_frame = ctk.CTkFrame(top, fg_color="transparent")
        options_frame.grid(row=2, column=1, columnspan=3, sticky="ew", padx=6, pady=(0, 10))

        self.v_recursive = tk.BooleanVar(value=self.s.input_recursive)
        self.chk_recursive = ctk.CTkCheckBox(
            options_frame,
            text="Include subfolders (recursive)",
            variable=self.v_recursive,
            command=self.refresh_found_count
        )
        self.chk_recursive.pack(side="left", padx=(0, 15))

        self.v_handle_ico = tk.BooleanVar(value=self.s.handle_ico)
        self.chk_handle_ico = ctk.CTkCheckBox(
            options_frame,
            text="Handle .ico (extract + rebuild)",
            variable=self.v_handle_ico,
            command=self.refresh_found_count
        )
        self.chk_handle_ico.pack(side="left", padx=15)

        self.v_strict_mode = tk.BooleanVar(value=self.s.strict_mode)
        self.chk_strict = ctk.CTkCheckBox(
            options_frame,
            text="Strict mode (fail on missing deps)",
            variable=self.v_strict_mode,
            width=180
        )
        self.chk_strict.pack(side="left", padx=15)

        self.lbl_found = ctk.CTkLabel(options_frame, text="Found: 0 inputs", font=ctk.CTkFont(slant="italic"))
        self.lbl_found.pack(side="left", padx=15)

        self.recent_var = tk.StringVar(value="Recent paths")
        self.recent_menu = ctk.CTkOptionMenu(
            options_frame,
            variable=self.recent_var,
            values=["Recent paths", "---"],
            width=140,
            command=self._on_recent_select
        )
        self.recent_menu.pack(side="left", padx=15)

        self.btn_dep_check = ctk.CTkButton(
            options_frame,
            text="Check deps",
            command=self._check_dependencies,
            width=90
        )
        self.btn_dep_check.pack(side="left", padx=15)

        self.theme_option = ctk.CTkOptionMenu(
            options_frame,
            values=["System", "Dark", "Light"],
            command=self.change_theme,
            width=100,
            fg_color=("#968596", "#736473"),
            button_color=("#968596", "#736473"),
            button_hover_color=("#ab9bab", "#5c4f5c"),
            text_color="white"
        )
        self.theme_option.pack(side="right", padx=(10, 0))
        self.theme_option.set(self.s.theme)

        theme_lbl = ctk.CTkLabel(options_frame, text="Theme:", font=ctk.CTkFont(weight="bold"))
        theme_lbl.pack(side="right")

        # --- CONTROLS GRID (2x2 Uniform) ---
        controls = ctk.CTkScrollableFrame(self, fg_color="transparent")
        controls.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        controls.grid_columnconfigure(0, weight=1, uniform="equal")
        controls.grid_columnconfigure(1, weight=1, uniform="equal")
        controls.grid_rowconfigure(0, weight=1, uniform="equal")
        controls.grid_rowconfigure(1, weight=1, uniform="equal")

        # A) Preprocess Card
        self.v_do_pre = tk.BooleanVar(value=self.s.do_preprocess)
        self.card_a = CardFrame(controls, "A) Preprocess", enable_var=self.v_do_pre, enable_callback=self._toggle_pre_mode_ui, header_fg_color=("#7d8c9b", "#5f6e82"))
        self.card_a.grid(row=0, column=0, padx=(0, 6), pady=(0, 6), sticky="nsew")

        c_a = self.card_a.content_frame
        c_a.grid_columnconfigure(0, weight=1)

        toggles_frame = ctk.CTkFrame(c_a, fg_color="transparent")
        toggles_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        toggles_frame.grid_columnconfigure(0, weight=1)
        toggles_frame.grid_columnconfigure(1, weight=1)

        self.v_gray = tk.BooleanVar(value=self.s.grayscale)
        self.v_autolvl = tk.BooleanVar(value=self.s.auto_level)
        self.v_cstretch = tk.BooleanVar(value=self.s.contrast_stretch)
        self.v_neg = tk.BooleanVar(value=self.s.negate)

        chk_gray = ctk.CTkCheckBox(toggles_frame, text="Grayscale", variable=self.v_gray)
        chk_gray.grid(row=0, column=0, sticky="w", pady=2)
        chk_autolvl = ctk.CTkCheckBox(toggles_frame, text="Auto-level", variable=self.v_autolvl)
        chk_autolvl.grid(row=0, column=1, sticky="w", pady=2)
        chk_cstretch = ctk.CTkCheckBox(toggles_frame, text="Contrast-stretch", variable=self.v_cstretch)
        chk_cstretch.grid(row=1, column=0, sticky="w", pady=2)
        chk_neg = ctk.CTkCheckBox(toggles_frame, text="Negate", variable=self.v_neg)
        chk_neg.grid(row=1, column=1, sticky="w", pady=2)

        self.v_med = tk.IntVar(value=self.s.median)
        self.scale_med = LabeledSlider(c_a, "Median Filter", from_=0, to=10, variable=self.v_med, resolution=1)
        self.scale_med.grid(row=1, column=0, sticky="ew", pady=4)

        self.v_blur = tk.DoubleVar(value=self.s.blur)
        self.scale_blur = LabeledSlider(c_a, "Gaussian Blur", from_=0.0, to=10.0, variable=self.v_blur, resolution=0.1)
        self.scale_blur.grid(row=2, column=0, sticky="ew", pady=4)

        mode_lbl = ctk.CTkLabel(c_a, text="Finish Mode", font=ctk.CTkFont(weight="bold"))
        mode_lbl.grid(row=3, column=0, sticky="w", pady=(6, 2))

        modes_frame = ctk.CTkFrame(c_a, fg_color="transparent")
        modes_frame.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        modes_frame.grid_columnconfigure(0, weight=1)
        modes_frame.grid_columnconfigure(1, weight=1)
        modes_frame.grid_columnconfigure(2, weight=1)

        self.v_mode = tk.StringVar(value=self.s.preprocess_mode)
        r_none = ctk.CTkRadioButton(modes_frame, text="None", value="none", variable=self.v_mode, command=self._toggle_pre_mode_ui)
        r_none.grid(row=0, column=0, sticky="w")
        r_th = ctk.CTkRadioButton(modes_frame, text="Threshold (B/W)", value="threshold", variable=self.v_mode, command=self._toggle_pre_mode_ui)
        r_th.grid(row=0, column=1, sticky="w")
        r_q = ctk.CTkRadioButton(modes_frame, text="Quantize (Gray)", value="quantize", variable=self.v_mode, command=self._toggle_pre_mode_ui)
        r_q.grid(row=0, column=2, sticky="w")

        self.v_th = tk.IntVar(value=self.s.threshold_pct)
        self.scale_th = LabeledSlider(c_a, "Threshold %", from_=0, to=100, variable=self.v_th, resolution=1)
        self.scale_th.grid(row=5, column=0, sticky="ew", pady=4)

        self.v_qlevels = tk.IntVar(value=self.s.quantize_levels)
        self.scale_q = LabeledSlider(c_a, "Quantize Levels", from_=2, to=256, variable=self.v_qlevels, resolution=1)
        self.scale_q.grid(row=6, column=0, sticky="ew", pady=4)

        # B) Pad Card
        self.v_do_pad = tk.BooleanVar(value=self.s.do_pad)
        self.card_b = CardFrame(controls, "B) Pad", enable_var=self.v_do_pad, header_fg_color=("#7d8c9b", "#5f6e82"))
        self.card_b.grid(row=0, column=1, padx=(6, 0), pady=(0, 6), sticky="nsew")

        c_b = self.card_b.content_frame
        c_b.grid_columnconfigure(0, weight=1)

        self.v_size = tk.IntVar(value=self.s.pad_size)
        self.scale_size = LabeledSlider(c_b, "Canvas Size", from_=16, to=2048, variable=self.v_size, resolution=16)
        self.scale_size.grid(row=0, column=0, sticky="ew", pady=8)

        dropdowns_frame = ctk.CTkFrame(c_b, fg_color="transparent")
        dropdowns_frame.grid(row=1, column=0, sticky="ew", pady=8)
        dropdowns_frame.grid_columnconfigure(0, weight=1)
        dropdowns_frame.grid_columnconfigure(1, weight=1)

        bg_lbl_frame = ctk.CTkFrame(dropdowns_frame, fg_color="transparent")
        bg_lbl_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        bg_lbl = ctk.CTkLabel(bg_lbl_frame, text="Background Color", font=ctk.CTkFont(size=12))
        bg_lbl.pack(anchor="w")
        self.v_bg = tk.StringVar(value=self.s.pad_bg)
        self.opt_bg = ctk.CTkOptionMenu(
            bg_lbl_frame, 
            variable=self.v_bg, 
            values=["white", "black", "transparent"],
            fg_color=("#9dacbb", "#7d8c9b"),
            button_color=("#9dacbb", "#7d8c9b"),
            button_hover_color=("#8ca0b5", "#5c6d80"),
            text_color="white"
        )
        self.opt_bg.pack(fill="x", pady=(2, 0))

        fmt_lbl_frame = ctk.CTkFrame(dropdowns_frame, fg_color="transparent")
        fmt_lbl_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        fmt_lbl = ctk.CTkLabel(fmt_lbl_frame, text="Output Format", font=ctk.CTkFont(size=12))
        fmt_lbl.pack(anchor="w")
        self.v_fmt = tk.StringVar(value=self.s.pad_out_fmt)
        self.opt_fmt = ctk.CTkOptionMenu(
            fmt_lbl_frame, 
            variable=self.v_fmt, 
            values=["png", "jpg"],
            fg_color=("#9dacbb", "#7d8c9b"),
            button_color=("#9dacbb", "#7d8c9b"),
            button_hover_color=("#8ca0b5", "#5c6d80"),
            text_color="white"
        )
        self.opt_fmt.pack(fill="x", pady=(2, 0))

        self.v_q = tk.IntVar(value=self.s.jpeg_quality)
        self.scale_q = LabeledSlider(c_b, "JPEG Quality", from_=50, to=100, variable=self.v_q, resolution=1)
        self.scale_q.grid(row=2, column=0, sticky="ew", pady=8)

        # C) Trace Card
        self.v_do_trace = tk.BooleanVar(value=self.s.do_trace)
        self.card_c = CardFrame(controls, "C) Trace → SVG", enable_var=self.v_do_trace, header_fg_color=("#7d8c9b", "#5f6e82"))
        self.card_c.grid(row=1, column=0, padx=(0, 6), pady=(6, 0), sticky="nsew")

        c_c = self.card_c.content_frame
        c_c.grid_columnconfigure(0, weight=1)

        self.v_cut = tk.IntVar(value=self.s.trace_cutoff_pct)
        self.scale_cut = LabeledSlider(c_c, "Cutoff %", from_=0, to=100, variable=self.v_cut, resolution=1)
        self.scale_cut.grid(row=0, column=0, sticky="ew", pady=8)

        self.v_trace_inv = tk.BooleanVar(value=self.s.trace_invert)
        self.chk_trace_inv = ctk.CTkCheckBox(c_c, text="Invert before threshold", variable=self.v_trace_inv)
        self.chk_trace_inv.grid(row=1, column=0, sticky="w", pady=8)

        self.v_turd = tk.IntVar(value=self.s.potrace_turdsize)
        self.scale_turd = LabeledSlider(c_c, "Turdsize (min speck)", from_=0, to=50, variable=self.v_turd, resolution=1)
        self.scale_turd.grid(row=2, column=0, sticky="ew", pady=8)

        self.v_smooth = tk.BooleanVar(value=self.s.potrace_smooth)
        self.chk_smooth = ctk.CTkCheckBox(c_c, text="Smooth curves (default)", variable=self.v_smooth)
        self.chk_smooth.grid(row=3, column=0, sticky="w", pady=8)

        # D) Export Card
        self.v_do_export = tk.BooleanVar(value=self.s.do_export)
        self.card_d = CardFrame(controls, "D) Export", enable_var=self.v_do_export, header_fg_color=("#7d8c9b", "#5f6e82"))
        self.card_d.grid(row=1, column=1, padx=(6, 0), pady=(6, 0), sticky="nsew")

        c_d = self.card_d.content_frame
        c_d.grid_columnconfigure(0, weight=1)

        self.v_w = tk.IntVar(value=self.s.export_width)
        self.scale_w = LabeledSlider(c_d, "Export Width", from_=16, to=4096, variable=self.v_w, resolution=16)
        self.scale_w.grid(row=0, column=0, sticky="ew", pady=12)

        self.v_area = tk.BooleanVar(value=self.s.export_area_drawing)
        self.chk_area = ctk.CTkCheckBox(c_d, text="Area: drawing (crop to graphics boundaries)", variable=self.v_area)
        self.chk_area.grid(row=1, column=0, sticky="w", pady=12)

        self.v_export_fmt = tk.StringVar(value=self.s.export_format)
        fmt_row = ctk.CTkFrame(c_d, fg_color="transparent")
        fmt_row.grid(row=2, column=0, sticky="ew", pady=12)
        fmt_lbl = ctk.CTkLabel(fmt_row, text="Export Format:", font=ctk.CTkFont(size=11))
        fmt_lbl.pack(side="left", padx=(0, 8))
        self.opt_export_fmt = ctk.CTkOptionMenu(
            fmt_row,
            variable=self.v_export_fmt,
            values=["png", "svg", "pdf", "eps"],
            width=100,
            fg_color=("#9dacbb", "#7d8c9b"),
            button_color=("#9dacbb", "#7d8c9b"),
            button_hover_color=("#8ca0b5", "#5c6d80"),
            text_color="white"
        )
        self.opt_export_fmt.pack(side="left")

        # --- ACTIONS PANEL ---
        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_run = ctk.CTkButton(
            btn,
            text="Run ALL (A→D)",
            command=self.run_all_clicked,
            width=160,
            fg_color=("#968596", "#736473"),
            hover_color=("#ab9bab", "#5c4f5c"),
            text_color="white",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_run.pack(side="left", padx=(0, 6))

        self.btn_defaults = ctk.CTkButton(
            btn,
            text="Icon-safe defaults",
            command=self.apply_icon_defaults,
            width=150,
            fg_color=("#968596", "#736473"),
            hover_color=("#ab9bab", "#5c4f5c"),
            text_color="white"
        )
        self.btn_defaults.pack(side="left", padx=6)

        self.v_skip_existing = tk.BooleanVar(value=self.s.skip_existing)
        self.chk_skip = ctk.CTkCheckBox(
            btn,
            text="Skip existing",
            variable=self.v_skip_existing,
            width=110
        )
        self.chk_skip.pack(side="left", padx=6)

        self.btn_open_out = ctk.CTkButton(
            btn,
            text="Open output folder",
            command=self.open_output_folder,
            width=150,
            fg_color=("#968596", "#736473"),
            hover_color=("#ab9bab", "#5c4f5c"),
            text_color="white"
        )
        self.btn_open_out.pack(side="left", padx=6)

        self.btn_open_log = ctk.CTkButton(
            btn,
            text="Open last log",
            command=self.open_last_log,
            width=120,
            fg_color=("#968596", "#736473"),
            hover_color=("#ab9bab", "#5c4f5c"),
            text_color="white"
        )
        self.btn_open_log.pack(side="left", padx=6)

        self.btn_clear_log = ctk.CTkButton(
            btn,
            text="Clear log",
            command=self.clear_log,
            width=100,
            fg_color=("#9dacbb", "#7d8c9b"),
            hover_color=("#8ca0b5", "#5c6d80"),
            text_color="white"
        )
        self.btn_clear_log.pack(side="right", padx=(6, 0))

        self.btn_copy_log = ctk.CTkButton(
            btn,
            text="Copy log",
            command=self.copy_log_to_clipboard,
            width=100,
            fg_color=("#9dacbb", "#7d8c9b"),
            hover_color=("#8ca0b5", "#5c6d80"),
            text_color="white"
        )
        self.btn_copy_log.pack(side="right", padx=6)

        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=10, pady=(10, 0))
        self.progress_frame.pack_forget()

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, mode="determinate", width=300)
        self.progress_bar.pack(side="left", padx=(0, 10))
        self.progress_bar.set(0)

        self.lbl_progress = ctk.CTkLabel(self.progress_frame, text="0/0 files", font=ctk.CTkFont(size=11))
        self.lbl_progress.pack(side="left")

        self.btn_cancel = ctk.CTkButton(
            self.progress_frame,
            text="Cancel",
            command=self.cancel_clicked,
            width=100,
            fg_color=("#c62828", "#ef5350"),
            hover_color=("#b71c1c", "#ff8a80"),
            text_color="white"
        )
        self.btn_cancel.pack(side="right")
        self.btn_cancel.pack_forget()

        # --- LOG TEXTBOX ---
        self.txt = ctk.CTkTextbox(self, wrap="word", state="disabled")
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt.bind("<Button-3>", self._on_log_right_click)
        self.txt.bind("<Double-Button-1>", self._on_log_double_click)

        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="Open output file", command=self._open_output_from_log)
        self._context_menu.add_command(label="Copy file path", command=self._copy_path_from_log)

        self._current_log_filename = None

        self.write(
            "Outputs:\n"
            "  A -> output\\01_preprocessed\n"
            "  B -> output\\02_padded\n"
            "  C -> output\\03_svg\n"
            "  D -> output\\04_export_png\n"
            "  ICO -> output\\05_ico\n\n"
        )

        self._toggle_pre_mode_ui()

    def _toggle_pre_mode_ui(self):
        if not self.v_do_pre.get():
            self.scale_th.configure_state("disabled")
            self.scale_q.configure_state("disabled")
            return

        mode = (self.v_mode.get() or "none").strip().lower()
        if mode == "threshold":
            self.scale_th.configure_state("normal")
            self.scale_q.configure_state("disabled")
        elif mode == "quantize":
            self.scale_th.configure_state("disabled")
            self.scale_q.configure_state("normal")
        else:
            self.scale_th.configure_state("disabled")
            self.scale_q.configure_state("disabled")

    def apply_icon_defaults(self):
        self.v_handle_ico.set(True)
        self.v_do_pre.set(True)
        self.v_do_pad.set(True)
        self.v_do_trace.set(False)
        self.v_do_export.set(False)

        self.v_gray.set(True)
        self.v_autolvl.set(True)
        self.v_cstretch.set(True)
        self.v_neg.set(False)
        self.v_med.set(0)
        self.v_blur.set(0.0)

        self.v_mode.set("quantize")
        self.v_qlevels.set(16)
        self.v_th.set(45)

        self.v_fmt.set("png")
        self.v_bg.set("transparent")
        self.v_size.set(256)
        self.v_q.set(95)

        self.v_w.set(256)
        self.v_area.set(True)

        self._toggle_pre_mode_ui()
        self.card_a.update_widgets_state()
        self.card_b.update_widgets_state()
        self.card_c.update_widgets_state()
        self.card_d.update_widgets_state()

        self.refresh_found_count()
        self.write("\nApplied icon-safe defaults.\n")

    # ---- browse ----
    def browse_input_file(self):
        p = filedialog.askopenfilename(
            title="Select input file",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.ico"),
                ("All files", "*.*"),
            ],
        )
        if p:
            self.v_in_path.set(p)
            self.on_input_path_changed()

    def browse_input_folder(self):
        p = filedialog.askdirectory(title="Select input folder")
        if p:
            self.v_in_path.set(p)
            self.on_input_path_changed()

    def browse_output_folder(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.v_out_path.set(p)

    # ---- logging ----
    def start_new_log_session(self):
        self.close_log_session()
        logs = Path.cwd() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = logs / f"lineforge_{stamp}.log"
        self._log_fh = open(self._log_path, "a", encoding="utf-8")
        self.write(f"--- Log: {self._log_path} ---\n")

    def close_log_session(self):
        try:
            if self._log_fh:
                self._log_fh.flush()
                self._log_fh.close()
        except Exception:
            pass
        self._log_fh = None

    def write(self, msg: str):
        self.txt.configure(state="normal")
        self.txt.insert("end", msg)
        self.txt.see("end")
        self.txt.configure(state="disabled")
        try:
            if self._log_fh:
                self._log_fh.write(msg)
                self._log_fh.flush()
        except Exception:
            pass

    def write_thread_safe(self, msg: str):
        self.after(0, lambda: self.write(msg))

    def clear_log(self):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.configure(state="disabled")

    def copy_log_to_clipboard(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.txt.get("1.0", "end-1c"))
            messagebox.showinfo("Log Copied", "Log content copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Copy Failed", str(e))

    def _on_log_right_click(self, event):
        self._current_log_filename = None
        idx = self.txt.index(f"@{event.x},{event.y}")
        line_start = self.txt.index(f"{idx} linestart")
        line_end = self.txt.index(f"{idx} lineend")
        line_text = self.txt.get(line_start, line_end).strip()
        match = LOG_FILENAME_PATTERN.search(line_text)
        if match:
            self._current_log_filename = match.group(1)
        self._context_menu.tk_popup(event.x_root, event.y_root)

    def _on_log_double_click(self, event):
        idx = self.txt.index(f"@{event.x},{event.y}")
        line_start = self.txt.index(f"{idx} linestart")
        line_end = self.txt.index(f"{idx} lineend")
        line_text = self.txt.get(line_start, line_end).strip()
        match = LOG_FILENAME_PATTERN.search(line_text)
        if match:
            self._open_output_from_log()

    def _open_output_from_log(self):
        if not self._current_log_filename:
            return
        try:
            out = Path(self.v_out_path.get().strip()).resolve()
            out_file = out / self._current_log_filename
            if out_file.exists():
                os.startfile(str(out_file))
            else:
                messagebox.showinfo("File not found", f"Could not find: {out_file}")
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def _copy_path_from_log(self):
        if not self._current_log_filename:
            return
        try:
            out = Path(self.v_out_path.get().strip()).resolve()
            out_file = out / self._current_log_filename
            self.clipboard_clear()
            self.clipboard_append(str(out_file))
        except Exception as e:
            messagebox.showerror("Copy failed", str(e))

    # ---- helpers ----
    def change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        self.s.theme = choice
        self.s.save()
        self.card_a.update_widgets_state()
        self.card_b.update_widgets_state()
        self.card_c.update_widgets_state()
        self.card_d.update_widgets_state()

    def on_input_path_changed(self, *args):
        p_str = self.v_in_path.get().strip()
        if not p_str:
            self.e_in.configure(border_color="#9b9b9b")
            self.lbl_found.configure(text="Found: 0 inputs")
            return

        p = Path(p_str)
        if p.exists():
            # Purple border
            self.e_in.configure(border_color=["#968596", "#736473"])
            self.refresh_found_count()
        else:
            # Red border
            self.e_in.configure(border_color=["#ef5350", "#c62828"])
            self.lbl_found.configure(text="Found: ? inputs (path invalid)")

    def sync(self):
        self.s.input_path = self.v_in_path.get().strip()
        self.s.output_path = self.v_out_path.get().strip()
        self.s.input_recursive = bool(self.v_recursive.get())
        self.s.handle_ico = bool(self.v_handle_ico.get())

        self.s.do_preprocess = bool(self.v_do_pre.get())
        self.s.do_pad = bool(self.v_do_pad.get())
        self.s.do_trace = bool(self.v_do_trace.get())
        self.s.do_export = bool(self.v_do_export.get())

        self.s.grayscale = bool(self.v_gray.get())
        self.s.auto_level = bool(self.v_autolvl.get())
        self.s.contrast_stretch = bool(self.v_cstretch.get())
        self.s.negate = bool(self.v_neg.get())
        self.s.median = int(self.v_med.get())
        self.s.blur = float(self.v_blur.get())

        self.s.preprocess_mode = (self.v_mode.get() or "none").strip().lower()
        self.s.threshold_pct = int(self.v_th.get())
        self.s.quantize_levels = int(self.v_qlevels.get())

        self.s.pad_size = int(self.v_size.get())
        self.s.pad_bg = self.v_bg.get().strip().lower()
        self.s.pad_out_fmt = self.v_fmt.get().strip().lower()
        self.s.jpeg_quality = int(self.v_q.get())

        self.s.trace_cutoff_pct = int(self.v_cut.get())
        self.s.trace_invert = bool(self.v_trace_inv.get())
        self.s.potrace_turdsize = int(self.v_turd.get())
        self.s.potrace_smooth = bool(self.v_smooth.get())

        self.s.export_width = int(self.v_w.get())
        self.s.export_area_drawing = bool(self.v_area.get())
        self.s.export_format = self.v_export_fmt.get().strip().lower()
        self.s.skip_existing = bool(self.v_skip_existing.get())
        self.s.strict_mode = bool(self.v_strict_mode.get())

    def _setup_keyboard_shortcuts(self):
        self.bind("<Control-o>", lambda e: self.browse_input_folder())
        self.bind("<Control-Return>", lambda e: self.run_all_clicked())
        self.bind("<Control-s>", lambda e: self.save_settings())
        self.bind("<Control-q>", lambda e: self.on_close())

    def save_settings(self):
        self.sync()
        self.s.save()
        self.write("\nSettings saved.\n")

    def _check_dependencies(self):
        deps = [
            ("vpipe-cli (LineForge Engine)", find_vpipe()),
        ]
        for name, path in deps:
            status = "OK" if path else "NOT FOUND"
            self.write(f"[Dependency] {name}: {status}\n")

    def _load_recent_inputs(self):
        recent = self.s.recent_inputs[:10]
        if recent:
            self.recent_menu.configure(values=["Recent paths"] + recent + ["---", "Clear history"])
        else:
            self.recent_menu.configure(values=["Recent paths", "---"])

    def _on_recent_select(self, choice):
        if choice == "Clear history":
            self.s.recent_inputs = []
            self.recent_menu.set("Recent paths")
            self._load_recent_inputs()
        elif choice != "Recent paths" and choice != "---":
            self.v_in_path.set(choice)
            self.recent_var.set("Recent paths")
            self.on_input_path_changed()

    def _update_recent_inputs(self, path: str):
        if path and path not in self.s.recent_inputs:
            self.s.recent_inputs.insert(0, path)
            self.s.recent_inputs = self.s.recent_inputs[:10]
            self._load_recent_inputs()

    def paths(self):
        inp = Path(self.v_in_path.get().strip())
        out = Path(self.v_out_path.get().strip())
        if not inp.exists():
            raise FileNotFoundError(f"Input path not found: {inp}")
        out.mkdir(parents=True, exist_ok=True)
        return inp, out

    def refresh_found_count(self):
        try:
            inp = Path(self.v_in_path.get().strip())
            recursive = bool(self.v_recursive.get())
            files = list_images(inp, recursive=recursive)
            self.lbl_found.configure(text=f"Found: {len(files)} inputs" + (" (recursive)" if recursive else ""))
        except Exception:
            self.lbl_found.configure(text="Found: ? inputs")

    def open_output_folder(self):
        try:
            out = Path(self.v_out_path.get().strip()).resolve()
            out.mkdir(parents=True, exist_ok=True)
            os.startfile(str(out))
        except Exception as e:
            messagebox.showerror("Open output folder failed", str(e))

    def open_last_log(self):
        try:
            if self._log_path and self._log_path.exists():
                os.startfile(str(self._log_path.resolve()))
                return
            logs = Path.cwd() / "logs"
            ls = sorted(logs.glob("lineforge_*.log"))
            if ls:
                os.startfile(str(ls[-1].resolve()))
            else:
                messagebox.showinfo("Open last log", "No log files found.")
        except Exception as e:
            messagebox.showerror("Open last log failed", str(e))

    def set_ui_state(self, state):
        entry_state = "normal" if state == "normal" else "readonly"
        self.e_in.configure(state=entry_state)
        self.e_out.configure(state=entry_state)

        self.chk_recursive.configure(state=state)
        self.chk_handle_ico.configure(state=state)

        self.btn_browse_in_file.configure(state=state)
        self.btn_browse_in_folder.configure(state=state)
        self.btn_browse_out.configure(state=state)

        self.btn_defaults.configure(state=state)
        self.btn_open_out.configure(state=state)
        self.btn_open_log.configure(state=state)
        self.btn_copy_log.configure(state=state)
        self.btn_clear_log.configure(state=state)

        self.theme_option.configure(state=state)

        if state == "disabled":
            self.card_a.set_enabled(False)
            self.card_b.set_enabled(False)
            self.card_c.set_enabled(False)
            self.card_d.set_enabled(False)
            self.card_a.chk_enable.configure(state="disabled")
            self.card_b.chk_enable.configure(state="disabled")
            self.card_c.chk_enable.configure(state="disabled")
            self.card_d.chk_enable.configure(state="disabled")
        else:
            self.card_a.chk_enable.configure(state="normal")
            self.card_b.chk_enable.configure(state="normal")
            self.card_c.chk_enable.configure(state="normal")
            self.card_d.chk_enable.configure(state="normal")
            self.card_a.update_widgets_state()
            self.card_b.update_widgets_state()
            self.card_c.update_widgets_state()
            self.card_d.update_widgets_state()

    def on_close(self):
        self.sync()
        self.s.theme = ctk.get_appearance_mode()
        self.s.save()
        self.close_log_session()
        self.destroy()

    # ---- run ----
    def run_all_clicked(self):
        self.start_new_log_session()
        self.sync()
        self._toggle_pre_mode_ui()
        try:
            inp, out = self.paths()
        except Exception as e:
            self.write(f"\nFAILED: {e}\n")
            messagebox.showerror("Run failed", str(e))
            return

        self._cancel_event.clear()
        self._total_files = 0
        self._current_file = 0
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="0/0 files")
        self.progress_frame.pack(fill="x", padx=10, pady=(10, 0))
        self.btn_cancel.pack(side="right")

        self.set_ui_state("disabled")
        self.btn_run.configure(text="Running...", state="disabled")

        def update_progress(current: int, total: int):
            self._current_file = current
            self._total_files = total
            pct = (current / total) if total > 0 else 0
            self.progress_bar.set(pct)
            self.lbl_progress.configure(text=f"{current}/{total} files")

        def run_thread():
            try:
                self.write_thread_safe("\nRunning ALL stages...\n")
                self._result = run_all(inp, out, self.s, self.write_thread_safe, update_progress)
                if self._cancel_event.is_set():
                    self.write_thread_safe("\n[Cancelled]\n")
                else:
                    self.write_thread_safe("\nDONE.\n")
                    self._show_stats()
                    self.after(0, self.open_output_folder)
            except Exception as e:
                self.write_thread_safe(f"\nFAILED: {e}\n")
                self.after(0, lambda ex=e: messagebox.showerror("Run failed", str(ex)))
            finally:
                self._update_recent_inputs(self.v_in_path.get().strip())
                self.after(0, lambda: self.set_ui_state("normal"))
                self.after(0, lambda: self.btn_run.configure(text="Run ALL (A→D)", state="normal"))
                self.after(0, lambda: self.progress_frame.pack_forget())
                self.after(0, lambda: self.btn_cancel.pack_forget())

        threading.Thread(target=run_thread, daemon=True).start()

    def cancel_clicked(self):
        cancel_pipeline()
        self.write_thread_safe("\n[Cancel requested...]\n")

    def _show_stats(self):
        if not self._result:
            return
        stats = self._result
        total_bytes = 0
        for stage, cnt in stats.stage_stats.items():
            self.write(f"  {stage}: {cnt} files\n")
        if stats.failed_files:
            self.write(f"\nFailed files ({len(stats.failed_files)}):\n")
            for f in stats.failed_files[:20]:
                self.write(f"  {f}\n")
            if len(stats.failed_files) > 20:
                self.write(f"  ... and {len(stats.failed_files) - 20} more\n")
        msg = f"\nCompleted: {stats.processed_files} files processed, {len(stats.failed_files)} failed.\n"
        self.write(msg)
