from pathlib import Path
import sys
import tkinter as tk

from PIL import Image, ImageTk


ICON_FILES = {
    "left": "left-click_2.png",
    "left_select": "left-click.png",
    "right": "right-click.png",
    "wheel": "scroll.png",
    "scroll": "scroll.png",
    "ctrl": "ctrl.png",
    "shift": "shift.png",
}


def create_mouse_icon(parent, highlight="right", size=(34, 46)):
    icon = create_asset_icon(parent, highlight, size)

    if icon is not None:
        return icon

    background = get_widget_background(parent)
    canvas = tk.Canvas(
        parent,
        width=size[0],
        height=size[1],
        highlightthickness=0,
        bg=background
    )
    draw_mouse_icon(canvas, highlight)
    return canvas


def create_shortcut_icon(parent, icon_names, size=(30, 30)):
    frame = tk.Frame(parent, bg=get_widget_background(parent))

    for index, icon_name in enumerate(icon_names):
        if index:
            tk.Label(frame, text="+", bg=frame.cget("background")).pack(side=tk.LEFT, padx=3)

        create_mouse_icon(frame, highlight=icon_name, size=size).pack(side=tk.LEFT)

    return frame


def create_asset_icon(parent, icon_name, size):
    icon_file = ICON_FILES.get(icon_name)

    if not icon_file:
        return None

    icon_path = get_resource_path("images", icon_file)

    if not icon_path.exists():
        return None

    image = Image.open(icon_path).convert("RGBA")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(image)
    label = tk.Label(parent, image=photo, bg=get_widget_background(parent), borderwidth=0)
    label.image = photo
    return label


def get_resource_path(*parts):
    base_path = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return base_path.joinpath(*parts)


def get_widget_background(widget):
    try:
        return widget.cget("background")
    except tk.TclError:
        return widget.winfo_toplevel().cget("background")


def draw_mouse_icon(canvas, highlight="right"):
    width = int(canvas["width"])
    height = int(canvas["height"])
    accent = "#0d6efd"
    outline = "#6c757d"
    fill = "#ffffff"
    muted = "#e9ecef"

    body_left = 5
    body_top = 3
    body_right = width - 5
    body_bottom = height - 4
    mid_x = width // 2
    button_bottom = 20

    canvas.create_oval(body_left, body_top, body_right, body_bottom, fill=fill, outline=outline, width=2)

    left_fill = accent if highlight == "left" else muted
    right_fill = accent if highlight == "right" else muted
    wheel_fill = accent if highlight == "wheel" else outline

    canvas.create_arc(body_left + 1, body_top + 1, body_right - 1, 30, start=90, extent=90, fill=left_fill, outline="")
    canvas.create_arc(body_left + 1, body_top + 1, body_right - 1, 30, start=0, extent=90, fill=right_fill, outline="")
    canvas.create_line(mid_x, body_top + 2, mid_x, button_bottom, fill=outline, width=1)
    canvas.create_line(body_left + 4, button_bottom, body_right - 4, button_bottom, fill=outline, width=1)
    canvas.create_oval(mid_x - 3, 9, mid_x + 3, 17, fill=wheel_fill, outline=wheel_fill)
    canvas.create_oval(body_left, body_top, body_right, body_bottom, outline=outline, width=2)
