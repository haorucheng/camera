"""Camera Studio - a small desktop camera application.

Dependencies:
    pip install -r requirements.txt

The application uses Tkinter for the GUI, OpenCV for camera capture, and
Pillow for rendering frames and saved photos in Tkinter.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import cv2
except ImportError:  # Keep the UI usable enough to explain how to fix setup.
    cv2 = None

try:
    from PIL import Image, ImageDraw, ImageOps, ImageTk
except ImportError:
    Image = ImageDraw = ImageOps = ImageTk = None


APP_TITLE = "Camera Studio"
DEFAULT_SIZE = "1280 x 720"
SIZES = {
    "640 x 480": (640, 480),
    "1280 x 720": (1280, 720),
    "1920 x 1080": (1920, 1080),
}


class CameraStudio(tk.Tk):
    """Camera preview, capture, and photo gallery window."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(900, 620)
        self.configure(bg="#111827")

        self.cap: Optional[object] = None
        self.latest_frame = None
        self.latest_photo: Optional[Path] = None
        self.preview_photo = None
        self.selected_photo = None
        self.viewing_photo = False
        self.running = False
        self.mirrored = tk.BooleanVar(value=True)
        self.camera_index = tk.StringVar(value="摄像头 0")
        self.resolution = tk.StringVar(value=DEFAULT_SIZE)
        self.status = tk.StringVar(value="准备就绪")
        self.counter_text = tk.StringVar(value="0 张照片")
        self.gallery_paths: list[Path] = []
        self.thumb_images: list[object] = []

        self.photo_dir = Path.home() / "Pictures" / "CameraStudio"
        self.photo_dir.mkdir(parents=True, exist_ok=True)

        self._build_style()
        self._build_ui()
        self._refresh_gallery()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<space>", lambda _event: self.take_photo())
        self.bind("<Control-s>", lambda _event: self.take_photo())
        self.after(80, self._update_preview)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background="#111827")
        style.configure("Panel.TFrame", background="#1f2937")
        style.configure("Title.TLabel", background="#111827", foreground="#f9fafb", font=("Segoe UI", 19, "bold"))
        style.configure("Subtle.TLabel", background="#111827", foreground="#9ca3af", font=("Segoe UI", 9))
        style.configure("Panel.TLabel", background="#1f2937", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.configure("PanelHeader.TLabel", background="#1f2937", foreground="#f9fafb", font=("Segoe UI", 11, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), foreground="#ffffff", background="#2563eb", padding=(12, 8))
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("disabled", "#374151")])
        style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(9, 6))
        style.configure("TCombobox", padding=5)
        style.configure("TCheckbutton", background="#1f2937", foreground="#e5e7eb")
        style.map("TCheckbutton", background=[("active", "#1f2937")])

    def _build_ui(self) -> None:
        header = ttk.Frame(self, style="App.TFrame", padding=(22, 18, 22, 10))
        header.pack(fill="x")
        ttk.Label(header, text="Camera Studio", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="轻量桌面相机 · 拍摄、预览与管理照片", style="Subtle.TLabel").pack(side="left", padx=(14, 0), pady=(6, 0))
        ttk.Label(header, textvariable=self.counter_text, style="Subtle.TLabel").pack(side="right", pady=(6, 0))

        body = ttk.Frame(self, style="App.TFrame", padding=(22, 6, 22, 18))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        preview_panel = ttk.Frame(body, style="Panel.TFrame", padding=12)
        preview_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        preview_panel.rowconfigure(1, weight=1)
        preview_panel.columnconfigure(0, weight=1)
        ttk.Label(preview_panel, text="实时预览", style="PanelHeader.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.preview_label = tk.Label(preview_panel, text="正在启动摄像头…", bg="#0b1220", fg="#9ca3af", font=("Segoe UI", 13))
        self.preview_label.grid(row=1, column=0, sticky="nsew")
        self.status_label = ttk.Label(preview_panel, textvariable=self.status, style="Panel.TLabel")
        self.status_label.grid(row=2, column=0, sticky="w", pady=(10, 0))

        side = ttk.Frame(body, style="Panel.TFrame", padding=14)
        side.grid(row=0, column=1, sticky="nsew")
        side.rowconfigure(7, weight=1)
        side.columnconfigure(0, weight=1)
        ttk.Label(side, text="拍摄控制", style="PanelHeader.TLabel").grid(row=0, column=0, sticky="w")

        ttk.Label(side, text="摄像头", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=(16, 4))
        camera_row = ttk.Frame(side, style="Panel.TFrame")
        camera_row.grid(row=2, column=0, sticky="ew")
        camera_row.columnconfigure(0, weight=1)
        self.camera_combo = ttk.Combobox(camera_row, textvariable=self.camera_index, values=[f"摄像头 {i}" for i in range(5)], state="readonly")
        self.camera_combo.grid(row=0, column=0, sticky="ew")
        self.camera_combo.bind("<<ComboboxSelected>>", self._switch_camera)

        ttk.Label(side, text="分辨率", style="Panel.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 4))
        self.size_combo = ttk.Combobox(side, textvariable=self.resolution, values=list(SIZES), state="readonly")
        self.size_combo.grid(row=4, column=0, sticky="ew")
        self.size_combo.bind("<<ComboboxSelected>>", self._change_resolution)

        ttk.Checkbutton(side, text="水平镜像预览", variable=self.mirrored, command=self._mirror_changed).grid(row=5, column=0, sticky="w", pady=(12, 10))
        self.capture_button = ttk.Button(side, text="●  拍照  (Space)", style="Accent.TButton", command=self.take_photo)
        self.capture_button.grid(row=6, column=0, sticky="ew", pady=(0, 14))
        ttk.Button(side, text="选择照片文件夹", style="Secondary.TButton", command=self.choose_folder).grid(row=7, column=0, sticky="new", pady=(0, 12))

        ttk.Label(side, text="最近照片", style="PanelHeader.TLabel").grid(row=8, column=0, sticky="w", pady=(2, 8))
        gallery_frame = ttk.Frame(side, style="Panel.TFrame")
        gallery_frame.grid(row=9, column=0, sticky="nsew")
        gallery_frame.columnconfigure(0, weight=1)
        gallery_frame.rowconfigure(0, weight=1)
        self.gallery = tk.Listbox(gallery_frame, height=7, bg="#111827", fg="#d1d5db", selectbackground="#2563eb", selectforeground="#ffffff", relief="flat", highlightthickness=0, activestyle="none", font=("Segoe UI", 9))
        self.gallery.grid(row=0, column=0, sticky="nsew")
        self.gallery.bind("<<ListboxSelect>>", self._gallery_selected)
        scroll = ttk.Scrollbar(gallery_frame, orient="vertical", command=self.gallery.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.gallery.configure(yscrollcommand=scroll.set)

        actions = ttk.Frame(side, style="Panel.TFrame")
        actions.grid(row=10, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Button(actions, text="打开文件夹", style="Secondary.TButton", command=self.open_folder).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(actions, text="删除选中", style="Secondary.TButton", command=self.delete_selected).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(side, text="返回实时预览", style="Secondary.TButton", command=self._return_to_live).grid(row=11, column=0, sticky="ew", pady=(8, 0))

    def _camera_number(self) -> int:
        try:
            return int(self.camera_index.get().split()[-1])
        except (ValueError, IndexError):
            return 0

    def _open_camera(self) -> None:
        if cv2 is None or Image is None:
            self.status.set("缺少依赖：请运行 pip install -r requirements.txt")
            self.preview_label.configure(text="无法启动摄像头\n请先安装 requirements.txt 中的依赖")
            return
        self._release_camera()
        index = self._camera_number()
        try:
            self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(index)
            if not self.cap.isOpened():
                self._release_camera()
                self.status.set(f"无法打开摄像头 {index}，请检查权限或设备")
                self.preview_label.configure(text="未检测到可用摄像头")
                return
            width, height = SIZES.get(self.resolution.get(), SIZES[DEFAULT_SIZE])
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.running = True
            self.status.set(f"摄像头 {index} 已连接 · 按 Space 拍照")
        except Exception as exc:
            self._release_camera()
            self.status.set(f"摄像头启动失败：{exc}")

    def _release_camera(self) -> None:
        self.running = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def _update_preview(self) -> None:
        if self.running and self.cap is not None:
            ok, frame = self.cap.read()
            if ok:
                self.latest_frame = frame
                if not self.viewing_photo:
                    self._display_frame(frame)
            else:
                self.status.set("读取摄像头画面失败")
        self.after(30, self._update_preview)

    def _display_frame(self, frame) -> None:
        if Image is None or cv2 is None:
            return
        if self.mirrored.get():
            frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        width = max(320, self.preview_label.winfo_width())
        height = max(240, self.preview_label.winfo_height())
        image.thumbnail((width - 10, height - 10), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_photo, text="")

    def _switch_camera(self, _event=None) -> None:
        self._open_camera()

    def _change_resolution(self, _event=None) -> None:
        if self.running:
            self._open_camera()

    def _mirror_changed(self) -> None:
        if self.latest_frame is not None:
            self._display_frame(self.latest_frame)

    def take_photo(self) -> None:
        if cv2 is None or self.latest_frame is None:
            messagebox.showinfo("无法拍照", "请先安装依赖并确认摄像头已成功连接。", parent=self)
            return
        frame = self.latest_frame.copy()
        self.viewing_photo = False
        if self.mirrored.get():
            frame = cv2.flip(frame, 1)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.photo_dir / f"photo_{timestamp}_{int(time.time() * 1000) % 1000:03d}.jpg"
        try:
            cv2.imwrite(str(path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            self.latest_photo = path
            self._refresh_gallery(select=path)
            self.status.set(f"已保存：{path.name}")
            self._flash_preview()
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc), parent=self)

    def _flash_preview(self) -> None:
        self.preview_label.configure(relief="solid", bd=2, highlightbackground="#60a5fa")
        self.after(100, lambda: self.preview_label.configure(relief="flat", bd=0))

    def _refresh_gallery(self, select: Optional[Path] = None) -> None:
        self.gallery_paths = sorted((p for p in self.photo_dir.glob("*.jpg") if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)
        self.gallery.delete(0, tk.END)
        for path in self.gallery_paths:
            self.gallery.insert(tk.END, f"{path.stem}   ·   {self._file_size(path)}")
        self.counter_text.set(f"{len(self.gallery_paths)} 张照片")
        if select in self.gallery_paths:
            index = self.gallery_paths.index(select)
            self.gallery.selection_set(index)
            self.gallery.see(index)
            self._show_photo(select)
        elif self.gallery_paths:
            self.gallery.selection_set(0)
            self._show_photo(self.gallery_paths[0])

    @staticmethod
    def _file_size(path: Path) -> str:
        size = path.stat().st_size
        return f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"

    def _gallery_selected(self, _event=None) -> None:
        selection = self.gallery.curselection()
        if selection and selection[0] < len(self.gallery_paths):
            self.viewing_photo = True
            self._show_photo(self.gallery_paths[selection[0]])

    def _return_to_live(self) -> None:
        self.viewing_photo = False
        if self.latest_frame is not None:
            self._display_frame(self.latest_frame)
        self.status.set("实时预览")

    def _show_photo(self, path: Path) -> None:
        if Image is None:
            return
        try:
            image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            self.selected_photo = image.copy()
            image.thumbnail((self.preview_label.winfo_width() - 10, self.preview_label.winfo_height() - 10), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self.preview_photo, text="")
            self.status.set(f"查看照片：{path.name}")
        except Exception as exc:
            self.status.set(f"无法显示照片：{exc}")

    def choose_folder(self) -> None:
        chosen = filedialog.askdirectory(initialdir=str(self.photo_dir), title="选择照片保存文件夹", parent=self)
        if chosen:
            self.photo_dir = Path(chosen)
            self.photo_dir.mkdir(parents=True, exist_ok=True)
            self._refresh_gallery()
            self.status.set(f"保存位置：{self.photo_dir}")

    def open_folder(self) -> None:
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.photo_dir)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{self.photo_dir}"')
            else:
                os.system(f'xdg-open "{self.photo_dir}"')
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc), parent=self)

    def delete_selected(self) -> None:
        selection = self.gallery.curselection()
        if not selection:
            messagebox.showinfo("删除照片", "请先在最近照片中选择一张照片。", parent=self)
            return
        path = self.gallery_paths[selection[0]]
        if messagebox.askyesno("删除照片", f"确定删除 {path.name} 吗？", parent=self):
            try:
                path.unlink()
                self._refresh_gallery()
                self.status.set("照片已删除")
            except OSError as exc:
                messagebox.showerror("删除失败", str(exc), parent=self)

    def _on_close(self) -> None:
        self._release_camera()
        self.destroy()


def main() -> None:
    app = CameraStudio()
    app._open_camera()
    app.mainloop()


if __name__ == "__main__":
    main()
