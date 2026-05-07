import threading
import tkinter as tk
import tkinter.font as tkfont
import ttkbootstrap as ttk
from ttkbootstrap.constants import PRIMARY, SECONDARY

from i18n import SUPPORTED_LANGUAGES, translate
from mouse_icons import create_shortcut_icon
from ui_dialogs import open_existing_survey_file


class StartScreen:
    def __init__(self, root):
        self.root = root
        self.ui_scale = self.get_start_screen_scale()
        self.language_var = tk.StringVar(value="IT")
        self.app_class = None
        self.app_preload_error = None
        self.app_preload_done = False
        self.app_preload_started = False

        language_frame = ttk.Frame(root, padding=self.scaled_pair(8, 8))
        language_frame.place(relx=1.0, rely=0.0, anchor=tk.NE)
        self.language_label = ttk.Label(language_frame, font=self.font(10))
        self.language_label.pack(side=tk.LEFT, padx=(0, self.scale_int(6)))
        self.language_combo = ttk.Combobox(
            language_frame,
            textvariable=self.language_var,
            state="readonly",
            values=SUPPORTED_LANGUAGES,
            width=5
        )
        self.language_combo.pack(side=tk.LEFT)
        self.language_combo.bind("<<ComboboxSelected>>", self.apply_language)

        self.frame = ttk.Frame(root, padding=self.scale_int(32))
        self.frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.title_label = ttk.Label(
            self.frame,
            text="Wi-Fi Heatmap Survey",
            font=self.font(24, "bold"),
            bootstyle=PRIMARY
        )
        self.title_label.pack(pady=(0, self.scale_int(6)))
        self.subtitle_label = ttk.Label(
            self.frame,
            text="",
            font=self.font(10)
        )
        self.subtitle_label.pack(pady=(0, self.scale_int(22)))

        self.main_panel = ttk.Frame(self.frame)
        self.main_panel.pack()

        self.actions_group = ttk.Frame(
            self.main_panel,
            padding=self.scale_int(18),
            borderwidth=1,
            relief=tk.SOLID
        )
        self.actions_group.pack(side=tk.LEFT, fill=tk.BOTH)
        self.configure_start_button_fonts()

        self.new_button = self.create_start_button(
            self.actions_group,
            self.start_new_survey,
            "confirm"
        )
        self.new_button.pack(pady=self.scale_int(5))
        self.open_button = self.create_start_button(
            self.actions_group,
            self.open_existing_survey,
            "main"
        )
        self.open_button.pack(pady=self.scale_int(5))
        self.exit_button = self.create_start_button(
            self.actions_group,
            self.root.destroy,
            "muted"
        )
        self.exit_button.pack(pady=(self.scale_int(14), 0))

        self.help_group = ttk.Frame(
            self.main_panel,
            padding=self.scale_int(18),
            borderwidth=1,
            relief=tk.SOLID
        )
        self.help_group.pack(side=tk.LEFT, fill=tk.BOTH, padx=(self.scale_int(18), 0))
        help_content = ttk.Frame(self.help_group)
        help_content.pack(expand=True)
        self.start_step_labels = []

        for icon_types in (("right",), ("left",), ("wheel",), ("ctrl", "wheel")):
            row = ttk.Frame(help_content)
            row.pack(anchor="w", pady=self.scale_int(5))
            icon_size = self.scale_int(30)
            create_shortcut_icon(row, icon_types, size=(icon_size, icon_size)).pack(side=tk.LEFT)
            label = ttk.Label(row, font=self.font(10), anchor="w")
            label.pack(side=tk.LEFT, padx=(self.scale_int(10), 0))
            self.start_step_labels.append(label)

        self.loading_frame = ttk.Frame(self.frame)
        self.loading_frame.pack(fill=tk.X, pady=(self.scale_int(18), 0))
        self.loading_label = ttk.Label(
            self.loading_frame,
            font=self.font(9),
            bootstyle=SECONDARY
        )
        self.loading_label.pack(anchor=tk.CENTER, pady=(0, self.scale_int(6)))
        self.loading_bar = ttk.Progressbar(
            self.loading_frame,
            mode="indeterminate",
            length=self.scale_int(360)
        )
        self.loading_bar.pack(anchor=tk.CENTER)

        self.copyright_label = ttk.Label(
            self.frame,
            font=self.font(9),
            bootstyle=SECONDARY
        )
        self.copyright_label.pack(pady=(self.scale_int(18), 0))
        self.set_start_actions_state(tk.DISABLED)
        self.apply_language()
        self.root.after(100, self.start_app_preload)

    def get_start_screen_scale(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        scale = min(screen_width / 1920, screen_height / 1080)
        return max(1.0, min(1.35, scale))

    def scale_int(self, value):
        return max(1, int(round(value * self.ui_scale)))

    def scaled_pair(self, x, y):
        return self.scale_int(x), self.scale_int(y)

    def font(self, size, weight=None):
        scaled_size = self.scale_int(size)
        if weight:
            return ("Segoe UI", scaled_size, weight)
        return ("Segoe UI", scaled_size)

    def configure_start_button_fonts(self):
        self.start_button_font = tkfont.Font(family="Segoe UI", size=self.scale_int(10))

    def create_start_button(self, parent, command, variant):
        colors = {
            "confirm": ("#18bc9c", "#2fc2a5"),
            "main": ("#2c3e50", "#415161"),
            "muted": ("#95a5a6", "#9faeae"),
        }
        background, active_background = colors[variant]

        button = tk.Button(
            parent,
            command=command,
            width=self.scale_button_width(28),
            font=self.start_button_font,
            padx=self.scale_int(10),
            pady=self.scale_int(5),
            cursor="hand2"
        )
        button.configure(
            background=background,
            foreground="#ffffff",
            activebackground=active_background,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0
        )
        return button

    def scale_button_width(self, width):
        return max(22, int(round(width / self.ui_scale * 1.08)))

    @property
    def language(self):
        return self.language_var.get().lower()

    def apply_language(self, _event=None):
        language = self.language
        self.root.title(translate(language, "app_title"))
        self.language_label.configure(text=translate(language, "language"))
        self.subtitle_label.configure(text=translate(language, "start_subtitle"))
        self.start_step_labels[0].configure(text=translate(language, "mouse_right_action"))
        self.start_step_labels[1].configure(text=translate(language, "mouse_left_action"))
        self.start_step_labels[2].configure(text=translate(language, "mouse_wheel_action"))
        self.start_step_labels[3].configure(text=translate(language, "mouse_ctrl_scroll_action"))
        self.copyright_label.configure(text=translate(language, "copyright"))
        self.new_button.configure(text=translate(language, "new_survey"))
        self.open_button.configure(text=translate(language, "open_existing_survey"))
        self.exit_button.configure(text=translate(language, "exit"))
        if self.app_preload_error is not None:
            loading_key = "loading_app_error"
        elif self.app_preload_done:
            loading_key = "loading_app_ready"
        else:
            loading_key = "loading_app"
        self.loading_label.configure(text=translate(language, loading_key))

    def set_start_actions_state(self, state):
        self.new_button.configure(state=state)
        self.open_button.configure(state=state)

    def start_new_survey(self):
        self.start_app(None)

    def open_existing_survey(self):
        csv_file = open_existing_survey_file(self.root)

        if csv_file:
            self.start_app(csv_file)

    def start_app_preload(self):
        if self.app_preload_started:
            return

        self.app_preload_started = True
        self.loading_bar.start(12)
        threading.Thread(target=self.preload_app_class, daemon=True).start()
        self.root.after(100, self.check_app_preload)

    def preload_app_class(self):
        try:
            from app import WifiHeatmapApp
            self.app_class = WifiHeatmapApp
        except Exception as exc:
            self.app_preload_error = exc
        finally:
            self.app_preload_done = True

    def check_app_preload(self):
        if not self.app_preload_done:
            self.root.after(100, self.check_app_preload)
            return

        self.loading_bar.stop()

        if self.app_preload_error is not None:
            self.loading_label.configure(text=translate(self.language, "loading_app_error"))
            return

        self.loading_label.configure(text=translate(self.language, "loading_app_ready"))
        self.set_start_actions_state(tk.NORMAL)

    def get_app_class(self):
        if self.app_class is not None:
            return self.app_class

        from app import WifiHeatmapApp
        self.app_class = WifiHeatmapApp
        return self.app_class

    def start_app(self, csv_file):
        app_class = self.get_app_class()
        self.frame.destroy()
        self.language_combo.master.destroy()
        app_class(self.root, csv_file, self.language)


def main():
    root = ttk.Window(themename="flatly")
    root.title("Wi-Fi Heatmap Survey")
    root.geometry("1200x800")
    root.state("zoomed")

    StartScreen(root)
    root.mainloop()


if __name__ == "__main__":
    main()
