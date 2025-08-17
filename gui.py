# gui.py
import customtkinter as ctk
import config
from logger import log
import platform
if platform.system() == "Windows":
    import ctypes

class AppGUI(ctk.CTk):
    def __init__(self, start_callback, stop_callback, toggle_callbacks):
        ctk.set_appearance_mode("system")
        super().__init__()
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.toggle_callbacks = toggle_callbacks

        self._hide_timer = None
        self._is_hidden = False

        self.title(config.WINDOW_TITLE)
        
        width, height = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        screen_width = self._get_screen_width()
        x = (screen_width - width) // 2
        y = 0
        self.geometry(f"{width}x{height}+{x}+{y}")
        self._original_y = y
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=config.WINDOW_BG_COLOR)
        self.wm_attributes("-transparentcolor", config.WINDOW_BG_COLOR)
        
        self._create_widgets()

        self.bind("<Enter>", self._on_mouse_enter)
        self.bind("<Leave>", self._on_mouse_leave)

        self._offset_x = 0
        self._offset_y = 0

        self._on_mouse_leave()

    def _on_press(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _on_release(self, event):
        self._offset_x = 0
        self._offset_y = 0

    def _on_motion(self, event):
        x = self.winfo_pointerx() - self._offset_x
        y = self.winfo_pointery() - self._offset_y
        
        screen_width = self._get_screen_width()
        screen_height = self._get_screen_height()
        width = self.winfo_width()
        height = self.winfo_height()

        snap_margin = 20
        if abs(x) < snap_margin:
            x = 0
        elif abs(screen_width - (x + width)) < snap_margin:
            x = screen_width - width
        
        if abs(y) < snap_margin:
            y = 0
        elif abs(screen_height - (y + height)) < snap_margin:
            y = screen_height - height

        self.geometry(f"+{x}+{y}")
        self._original_y = y

    def _create_widgets(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.pack(expand=True, fill="both", padx=5, pady=5)
        self.main_frame.bind("<Enter>", self._on_mouse_enter)
        self.main_frame.bind("<Leave>", self._on_mouse_leave)

        self.entry_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.entry_frame.pack(pady=5, padx=5)

        self.room_id_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="请输入直播间ID", font=(config.FONT_FAMILY, config.FONT_SIZE_NORMAL))
        self.room_id_entry.pack(side="left", padx=(0, 10))

        self.start_button = ctk.CTkButton(self.entry_frame, text="开始", font=(config.FONT_FAMILY, config.FONT_SIZE_NORMAL), command=self._start, width=50)
        self.start_button.pack(side="left")

        self.stop_button = ctk.CTkButton(self.entry_frame, text="停止", font=(config.FONT_FAMILY, config.FONT_SIZE_NORMAL), command=self.stop_callback, width=50)
        self.stop_button.pack(side="left", padx=5)

        self.checkbox_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.checkbox_frame.pack(pady=5)

        checkboxes = {
            "chat": "聊天",
            "gift": "礼物",
            "follow": "关注",
            "welcome": "进场",
        }

        for i, (key, text) in enumerate(checkboxes.items()):
            var = ctk.BooleanVar()
            cb = ctk.CTkCheckBox(
                self.checkbox_frame,
                width=18,
                border_width=2,
                text=text,
                variable=var,
                command=self.toggle_callbacks[key],
            )
            cb.grid(row=0, column=i, padx=10, pady=0)

        self.label = ctk.CTkLabel(self.main_frame, text="直播间人数", font=(config.FONT_FAMILY, config.FONT_SIZE_LARGE))
        self.label.pack(pady=5)

        # Bind dragging to non-interactive widgets to allow buttons to be clicked
        for widget in [self.main_frame, self.label]:
            widget.bind("<ButtonPress-1>", self._on_press)
            widget.bind("<ButtonRelease-1>", self._on_release)
            widget.bind("<B1-Motion>", self._on_motion)

    def _start(self):
        room_id = self.room_id_entry.get()
        if room_id.isdigit():
            self.start_callback(room_id)
        else:
            log.warning("Invalid Room ID. It must be a number.")

    def update_viewers_count(self, count):
        self.label.configure(text=f"当前观看：{count} 人")

    def _on_mouse_enter(self, event=None):
        if self._hide_timer is not None:
            self.after_cancel(self._hide_timer)
            self._hide_timer = None
        if self._is_hidden:
            self._show_window()

    def _on_mouse_leave(self, event=None):
        if self._hide_timer is not None:
            self.after_cancel(self._hide_timer)
        self._hide_timer = self.after(1000, self._hide_window)

    def _hide_window(self):
        if not self._is_hidden:
            self._is_hidden = True
            x = self.winfo_x()
            height = self.winfo_height()
            new_y = -int(height * 0.65)  # 隐藏90%的高度
            self.geometry(f"+{x}+{new_y}")

    def _show_window(self):
        if self._is_hidden:
            self._is_hidden = False
            x = self.winfo_x()
            self.geometry(f"+{x}+{self._original_y}")

    def _get_screen_width(self):
        if platform.system() == "Windows":
            try:
                user32 = ctypes.windll.user32
                return user32.GetSystemMetrics(0)
            except Exception:
                return self.winfo_screenwidth()
        else:
            return self.winfo_screenwidth()

    def _get_screen_height(self):
        if platform.system() == "Windows":
            try:
                user32 = ctypes.windll.user32
                return user32.GetSystemMetrics(1)
            except Exception:
                return self.winfo_screenheight()
        else:
            return self.winfo_screenheight()

    def run(self):
        self.mainloop()
