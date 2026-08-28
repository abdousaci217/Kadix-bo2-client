import json
import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import pystray
from PIL import Image, ImageTk, ImageDraw

APP_NAME = "KADIX T6 CLIENT"
CONFIG_FILE = "kadix_t6_config.json"
SKINS_DIR = "Skins"

LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
PLUTONIUM_T6_IMAGES_DIR = os.path.join(LOCAL_APPDATA, r"Plutonium\storage\t6\images")
PLUTONIUM_T6_SCRIPTS_DIR = os.path.join(LOCAL_APPDATA, r"Plutonium\storage\t6\scripts")


class KadixManager:

  def __init__(self):
    self.config = self.load_config()

  def load_config(self):
    if os.path.exists(CONFIG_FILE):
      try:
        with open(CONFIG_FILE, "r") as f:
          return json.load(f)
      except Exception:
        return {"game_path": ""}
    return {"game_path": ""}

  def save_config(self):
    with open(CONFIG_FILE, "w") as f:
      json.dump(self.config, f)

  def get_game_path(self):
    return self.config.get("game_path", "")

  def validate_game_path(self, path):
    return os.path.exists(os.path.join(path, "t6mp.exe")) or os.path.exists(
        os.path.join(path, "t6zm.exe")
    )

  def install_file(self, source_path):
    if not os.path.exists(source_path):
      raise FileNotFoundError("Source file not found.")

    file_name = os.path.basename(source_path)
    file_lower = file_name.lower()

    if file_lower.endswith(".iwi"):
      destination_dir = PLUTONIUM_T6_IMAGES_DIR
    elif file_lower.endswith((".gsc", ".csc", ".ff")):
      destination_dir = PLUTONIUM_T6_SCRIPTS_DIR
    else:
      destination_dir = PLUTONIUM_T6_IMAGES_DIR

    os.makedirs(destination_dir, exist_ok=True)
    shutil.copy2(source_path, os.path.join(destination_dir, file_name))
    return file_name

  def scan_skins_catalog(self):
    categories = ["WEAPONS", "GLOVES", "UI", "BACKGROUNDS"]
    catalog = {cat: [] for cat in categories}

    if not os.path.exists(SKINS_DIR):
      os.makedirs(SKINS_DIR, exist_ok=True)

    existing_dirs = os.listdir(SKINS_DIR)

    for cat in categories:
      matched_dir_name = None
      for d in existing_dirs:
        if d.lower() == cat.lower():
          matched_dir_name = d
          break

      if not matched_dir_name:
        continue

      cat_folder = os.path.join(SKINS_DIR, matched_dir_name)
      if not os.path.isdir(cat_folder):
        continue

      try:
        sub_entries = os.listdir(cat_folder)
      except Exception:
        continue

      for sub_item in sub_entries:
        sub_item_path = os.path.join(cat_folder, sub_item)
        if not os.path.isdir(sub_item_path):
          continue

        try:
          bundle_files = os.listdir(sub_item_path)
        except Exception:
          continue

        iwi_files = []
        img_file = None

        for f in bundle_files:
          f_lower = f.lower()
          if f_lower.endswith(".iwi") or f_lower.endswith(".ff"):
            iwi_files.append(f)
          elif f_lower.endswith(".png"):
            img_file = f

        if not iwi_files:
          continue

        pretty_name = sub_item.replace("_", " ").title()

        if cat == "UI":
          sub_label = "HD UI Element / HUD"
        elif cat == "WEAPONS":
          sub_label = "Weapon Texture / Camo"
        elif cat == "GLOVES":
          sub_label = "Custom Player Gloves"
        else:
          sub_label = "Exclusive Menu Wallpaper"

        catalog[cat].append({
            "name": pretty_name,
            "type": sub_label,
            "bundle_folder": f"{matched_dir_name}/{sub_item}",
            "image_filename": img_file,
            "iwi_filenames": iwi_files,
        })

    return catalog


class KadixClientGUI:

  def __init__(self, root):
    self.root = root
    self.root.title(APP_NAME)
    self.root.geometry("980x880")
    self.root.overrideredirect(True)

    self.set_app_icon()
    self.root.after(10, self.enable_taskbar_integration)

    self.manager = KadixManager()

    # Theme Colors - Pure Black Matching
    self.bg_main = "#000000"
    self.bg_card = "#000000"
    self.bg_input = "#050505"
    self.text_red = "#ef4444"
    self.btn_red = "#b91c1c"
    self.btn_hover = "#dc2626"
    self.btn_green = "#10b981"
    self.btn_green_hover = "#059669"
    self.fg_muted = "#71717a"

    self.root.configure(bg=self.bg_main)
    self.tray_icon = None

    self.drag_offset_x = 0
    self.drag_offset_y = 0

    self.create_window_frame()
    self.check_first_run()

  def set_app_icon(self):
    if os.path.exists("icon.ico"):
      try:
        self.root.iconbitmap("icon.ico")
      except Exception:
        pass

  def enable_taskbar_integration(self):
    try:
      import ctypes

      GWL_EXSTYLE = -20
      WS_EX_APPWINDOW = 0x00040000
      WS_EX_TOOLWINDOW = 0x00000080

      hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
      if not hwnd:
        hwnd = self.root.winfo_id()

      style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
      style = style & ~WS_EX_TOOLWINDOW
      style = style | WS_EX_APPWINDOW
      ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

      self.root.wm_withdraw()
      self.root.wm_deiconify()
    except Exception:
      pass

  def start_window_drag(self, event):
    self.drag_offset_x = event.x
    self.drag_offset_y = event.y

  def do_window_drag(self, event):
    x = self.root.winfo_x() + (event.x - self.drag_offset_x)
    y = self.root.winfo_y() + (event.y - self.drag_offset_y)
    self.root.geometry(f"+{x}+{y}")

  def create_window_frame(self):
    self.main_container = tk.Frame(
        self.root,
        bg=self.bg_main,
        highlightbackground=self.text_red,
        highlightthickness=1,
    )
    self.main_container.pack(fill=tk.BOTH, expand=True)

    self.header_bar = tk.Frame(self.main_container, bg=self.bg_main, height=45)
    self.header_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(6, 5))
    self.header_bar.pack_propagate(False)

    self.header_bar.bind("<Button-1>", self.start_window_drag)
    self.header_bar.bind("<B1-Motion>", self.do_window_drag)

    title_lbl = tk.Label(
        self.header_bar,
        text=f"> {APP_NAME} _",
        bg=self.bg_main,
        fg=self.text_red,
        font=("Consolas", 13, "bold"),
    )
    title_lbl.pack(side=tk.LEFT, pady=8)
    title_lbl.bind("<Button-1>", self.start_window_drag)
    title_lbl.bind("<B1-Motion>", self.do_window_drag)

    close_btn = tk.Button(
        self.header_bar,
        text="[ X ]",
        bg=self.bg_main,
        fg=self.fg_muted,
        activebackground=self.btn_red,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 9, "bold"),
        command=self.exit_app,
    )
    close_btn.pack(side=tk.RIGHT, padx=(2, 0), ipady=4)

    min_btn = tk.Button(
        self.header_bar,
        text="[ _ ]",
        bg=self.bg_main,
        fg=self.fg_muted,
        activebackground=self.bg_card,
        activeforeground=self.text_red,
        bd=0,
        font=("Consolas", 9, "bold"),
        command=self.hide_to_tray,
    )
    min_btn.pack(side=tk.RIGHT, padx=2, ipady=4)

    support_btn = tk.Button(
        self.header_bar,
        text="[ $ SUPPORT ]",
        bg=self.bg_main,
        fg=self.btn_green,
        activebackground=self.btn_green,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 9, "bold"),
        command=lambda: self.copy_to_clipboard("TX7bxQXyyomx7dRxt6cxxjAmyps7QAx7b4"),
    )
    support_btn.pack(side=tk.RIGHT, padx=4, ipady=4)

    refresh_btn = tk.Button(
        self.header_bar,
        text="[ ↻ REFRESH ]",
        bg=self.bg_main,
        fg=self.fg_muted,
        activebackground=self.bg_card,
        activeforeground=self.text_red,
        bd=0,
        font=("Consolas", 9, "bold"),
        command=self.refresh_client_workspace,
    )
    refresh_btn.pack(side=tk.RIGHT, padx=4, ipady=4)

    tabs_frame = tk.Frame(self.header_bar, bg=self.bg_main)
    tabs_frame.pack(side=tk.RIGHT, padx=10, pady=5)

    self.tab_mods_btn = self.create_tab_button(
        tabs_frame, "[ MODS ]", lambda: self.switch_tab("mods")
    )
    self.tab_skins_btn = self.create_tab_button(
        tabs_frame, "[ SKINS ]", lambda: self.switch_tab("skins")
    )
    self.tab_sets_btn = self.create_tab_button(
        tabs_frame, "[ SETTINGS ]", lambda: self.switch_tab("settings")
    )

    self.sub_header = tk.Frame(self.main_container, bg=self.bg_card, height=38)
    self.sub_header.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(0, 10))
    self.sub_header.pack_propagate(False)

    self.search_entry = tk.Entry(
        self.sub_header,
        bg=self.bg_input,
        fg=self.text_red,
        insertbackground=self.text_red,
        bd=0,
        font=("Consolas", 9),
    )
    self.search_entry.pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=12, ipady=4
    )
    self.search_entry.insert(0, "C:\\> search modules...")
    self.search_entry.bind(
        "<FocusIn>",
        lambda e: self.search_entry.delete(0, tk.END)
        if self.search_entry.get() == "C:\\> search modules..."
        else None,
    )

    self.content_card = tk.Frame(
        self.main_container,
        bg=self.bg_card,
        highlightbackground="#18181b",
        highlightthickness=1,
    )
    self.content_card.pack(
        side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(0, 12)
    )

    self.current_tab_name = "mods"
    self.switch_tab("mods")

  def refresh_client_workspace(self):
    if hasattr(self, "skins_catalog"):
      self.skins_catalog = self.manager.scan_skins_catalog()
    self.switch_tab(self.current_tab_name)
    self.log_msg("[SYSTEM] Workspace refreshed successfully.")

  def create_tray_image(self):
    if os.path.exists("icon.ico"):
      try:
        return Image.open("icon.ico")
      except Exception:
        pass
    image = Image.new("RGB", (64, 64), "#000000")
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=self.btn_red)
    return image

  def hide_to_tray(self):
    self.root.withdraw()
    if not self.tray_icon:
      menu = pystray.Menu(
          pystray.MenuItem("[ SHOW ]", self.show_from_tray, default=True),
          pystray.MenuItem("[ QUIT ]", self.exit_from_tray),
      )
      self.tray_icon = pystray.Icon(
          "KadixT6Client", self.create_tray_image(), APP_NAME, menu
      )
    threading.Thread(target=self.tray_icon.run, daemon=True).start()

  def show_from_tray(self, icon, item):
    if self.tray_icon:
      self.tray_icon.stop()
      self.tray_icon = None
    self.root.after(0, self.root.deiconify)

  def exit_from_tray(self, icon, item):
    if self.tray_icon:
      self.tray_icon.stop()
    self.root.after(0, self.exit_app)

  def exit_app(self):
    if self.tray_icon:
      self.tray_icon.stop()
    self.root.destroy()

  def create_tab_button(self, parent, text, command):
    btn = tk.Button(
        parent,
        text=text,
        bg=self.bg_card,
        fg=self.fg_muted,
        activebackground=self.btn_red,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 9, "bold"),
        command=command,
        padx=8,
        pady=4,
    )
    btn.pack(side=tk.LEFT, padx=3)
    return btn

  def switch_tab(self, tab_name):
    self.current_tab_name = tab_name

    for btn in [
        self.tab_mods_btn,
        self.tab_skins_btn,
        self.tab_sets_btn,
    ]:
      btn.config(bg=self.bg_card, fg=self.fg_muted)

    for widget in self.content_card.winfo_children():
      widget.destroy()

    if tab_name == "mods":
      self.tab_mods_btn.config(bg=self.btn_red, fg="#ffffff")
      self.build_mods_panel()
    elif tab_name == "skins":
      self.tab_skins_btn.config(bg=self.btn_red, fg="#ffffff")
      self.build_skins_panel()
    elif tab_name == "settings":
      self.tab_sets_btn.config(bg=self.btn_red, fg="#ffffff")
      self.build_settings_panel()

  def build_mods_panel(self):
    lbl = tk.Label(
        self.content_card,
        text="C:\\> deploy_mod_package --target=storage/t6/scripts",
        bg=self.bg_card,
        fg=self.text_red,
        font=("Consolas", 10, "bold"),
    )
    lbl.pack(anchor="w", padx=18, pady=(15, 8))

    file_frame = tk.Frame(self.content_card, bg=self.bg_card)
    file_frame.pack(fill=tk.X, padx=18, pady=5)

    self.mod_entry = tk.Entry(
        file_frame,
        bg=self.bg_input,
        fg=self.text_red,
        insertbackground=self.text_red,
        bd=0,
        font=("Consolas", 10),
    )
    self.mod_entry.pack(
        side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10)
    )

    browse_btn = tk.Button(
        file_frame,
        text="ADD MOD",
        bg=self.btn_red,
        fg="#ffffff",
        activebackground=self.btn_hover,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 9, "bold"),
        command=self.browse_mod_file,
        padx=15,
    )
    browse_btn.pack(side=tk.RIGHT, ipady=4)

    deploy_btn = tk.Button(
        self.content_card,
        text="INSTALL MOD / SCRIPT",
        bg=self.btn_red,
        fg="#ffffff",
        activebackground=self.btn_hover,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 10, "bold"),
        command=self.install_mod_action,
    )
    deploy_btn.pack(fill=tk.X, padx=18, pady=(10, 8), ipady=10)

    info_frame = tk.Frame(
        self.content_card,
        bg=self.bg_input,
        highlightbackground="#18181b",
        highlightthickness=1,
    )
    info_frame.pack(fill=tk.X, padx=18, pady=(0, 10))

    info_title = tk.Label(
        info_frame,
        text="[ DESTINATION DIRECTORY PATHS ]",
        bg=self.bg_input,
        fg=self.text_red,
        font=("Consolas", 8, "bold"),
    )
    info_title.pack(anchor="w", padx=12, pady=(6, 2))

    specs_text = (
        f"• Images/Textures (.iwi) -> %localappdata%\\Plutonium\\storage\\t6\\images\n"
        f"• Scripts (.gsc/.csc) -> %localappdata%\\Plutonium\\storage\\t6\\scripts"
    )
    specs_lbl = tk.Label(
        info_frame,
        text=specs_text,
        bg=self.bg_input,
        fg=self.text_red,
        font=("Consolas", 8),
        justify=tk.LEFT,
    )
    specs_lbl.pack(anchor="w", padx=12, pady=(0, 6))

    # Clean text branding banner instead of background video loop
    logo_container = tk.Frame(
        self.content_card,
        bg=self.bg_input,
        highlightbackground="#18181b",
        highlightthickness=1,
    )
    logo_container.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 10))

    branding_lbl = tk.Label(
        logo_container,
        text="> KADIX T6 // SECURE COMPANION INTERFACE\n[ READY FOR USER CUSTOM SKINS & MODS ]",
        bg=self.bg_input,
        fg=self.text_red,
        font=("Consolas", 11, "bold"),
        justify=tk.CENTER,
    )
    branding_lbl.pack(expand=True)

    self.log_box = tk.Text(
        self.content_card,
        height=3,
        bg=self.bg_input,
        fg=self.text_red,
        bd=0,
        font=("Consolas", 9),
        state="disabled",
        wrap="word",
    )
    self.log_box.pack(fill=tk.X, padx=18, pady=(0, 12))

  def build_skins_panel(self):
    lbl = tk.Label(
        self.content_card,
        text=f"C:\\> skins_shop --grid-cards-expanded",
        bg=self.bg_card,
        fg=self.text_red,
        font=("Consolas", 10, "bold"),
    )
    lbl.pack(anchor="w", padx=18, pady=(12, 5))

    self.skins_catalog = self.manager.scan_skins_catalog()

    top_ctrl_bar = tk.Frame(self.content_card, bg=self.bg_card)
    top_ctrl_bar.pack(fill=tk.X, padx=18, pady=(0, 10))

    cat_bar = tk.Frame(top_ctrl_bar, bg=self.bg_card)
    cat_bar.pack(side=tk.LEFT)

    self.category_buttons = {}
    for cat_name in self.skins_catalog.keys():
      btn = tk.Button(
          cat_bar,
          text=f"[ {cat_name} ]",
          bg=self.bg_input,
          fg=self.fg_muted,
          activebackground=self.btn_red,
          activeforeground="#ffffff",
          bd=0,
          font=("Consolas", 8, "bold"),
          command=lambda c=cat_name: self.load_skin_category(c),
          padx=10,
          pady=5,
      )
      btn.pack(side=tk.LEFT, padx=(0, 6))
      self.category_buttons[cat_name] = btn

    add_pack_btn = tk.Button(
        top_ctrl_bar,
        text="[ ADD+ PACK ]",
        bg=self.btn_green,
        fg="#ffffff",
        activebackground=self.btn_green_hover,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 8, "bold"),
        command=self.add_custom_skin_pack,
        padx=10,
        pady=5,
    )
    add_pack_btn.pack(side=tk.LEFT, padx=(6, 0))

    self.remove_all_btn = tk.Button(
        top_ctrl_bar,
        text="[ REMOVE ALL ]",
        bg="#7f1d1d",
        fg="#ffffff",
        activebackground=self.btn_red,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 8, "bold"),
        command=self.remove_all_current_category,
        padx=10,
        pady=5,
    )
    self.remove_all_btn.pack(side=tk.RIGHT)

    container = tk.Frame(self.content_card, bg=self.bg_card)
    container.pack(fill=tk.BOTH, expand=True, padx=18, pady=5)

    self.canvas = tk.Canvas(container, bg=self.bg_card, highlightthickness=0)
    self.skins_display_frame = tk.Frame(self.canvas, bg=self.bg_card)

    self.skins_display_frame.bind(
        "<Configure>",
        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
    )

    self.canvas_window = self.canvas.create_window(
        (0, 0), window=self.skins_display_frame, anchor="nw"
    )

    self.canvas.bind(
        "<Configure>",
        lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
    )

    def _on_mousewheel(event):
      self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
    self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    self.load_skin_category("WEAPONS")

  def show_modern_info_dialog(self, title_text, msg_text):
    dialog = tk.Toplevel(self.root)
    dialog.title(title_text)
    dialog.geometry("480x260")
    dialog.configure(bg=self.bg_main)
    dialog.overrideredirect(True)
    dialog.grab_set()

    x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 240
    y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 130
    dialog.geometry(f"+{x}+{y}")

    container = tk.Frame(dialog, bg=self.bg_main, highlightbackground=self.text_red, highlightthickness=1)
    container.pack(fill=tk.BOTH, expand=True)

    title_lbl = tk.Label(container, text=f"> {title_text} _", bg=self.bg_main, fg=self.text_red, font=("Consolas", 11, "bold"))
    title_lbl.pack(anchor="w", padx=16, pady=(15, 10))

    msg_lbl = tk.Label(container, text=msg_text, bg=self.bg_main, fg="#ffffff", font=("Consolas", 10), justify=tk.LEFT)
    msg_lbl.pack(anchor="w", padx=16, pady=5)

    ok_btn = tk.Button(container, text="[ PROCEED ]", bg=self.btn_red, fg="#ffffff", activebackground=self.btn_hover, activeforeground="#ffffff", bd=0, font=("Consolas", 9, "bold"), command=dialog.destroy)
    ok_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=16, ipady=8)

    self.root.wait_window(dialog)

  def show_modern_input_dialog(self, title_text, prompt_text):
    dialog = tk.Toplevel(self.root)
    dialog.title(title_text)
    dialog.geometry("420x210")
    dialog.configure(bg=self.bg_main)
    dialog.overrideredirect(True)
    dialog.grab_set()

    x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 210
    y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 105
    dialog.geometry(f"+{x}+{y}")

    container = tk.Frame(dialog, bg=self.bg_main, highlightbackground=self.text_red, highlightthickness=1)
    container.pack(fill=tk.BOTH, expand=True)

    title_lbl = tk.Label(container, text=f"> {title_text} _", bg=self.bg_main, fg=self.text_red, font=("Consolas", 11, "bold"))
    title_lbl.pack(anchor="w", padx=16, pady=(15, 5))

    prompt_lbl = tk.Label(container, text=prompt_text, bg=self.bg_main, fg="#ffffff", font=("Consolas", 9))
    prompt_lbl.pack(anchor="w", padx=16, pady=(5, 5))

    entry_var = tk.StringVar()
    entry_box = tk.Entry(container, textvariable=entry_var, bg=self.bg_input, fg=self.text_red, insertbackground=self.text_red, bd=0, font=("Consolas", 11))
    entry_box.pack(fill=tk.X, padx=16, pady=8, ipady=6)
    entry_box.focus_set()

    result = [None]

    def on_submit(event=None):
      result[0] = entry_var.get().strip()
      dialog.destroy()

    entry_box.bind("<Return>", on_submit)

    btn_frame = tk.Frame(container, bg=self.bg_main)
    btn_frame.pack(fill=tk.X, padx=16, pady=(5, 15))

    submit_btn = tk.Button(btn_frame, text="[ CONFIRM ]", bg=self.btn_green, fg="#ffffff", activebackground=self.btn_green_hover, activeforeground="#ffffff", bd=0, font=("Consolas", 9, "bold"), command=on_submit)
    submit_btn.pack(side=tk.RIGHT, ipady=6, ipadx=12)

    cancel_btn = tk.Button(btn_frame, text="[ CANCEL ]", bg=self.bg_input, fg=self.fg_muted, activebackground=self.btn_red, activeforeground="#ffffff", bd=0, font=("Consolas", 9, "bold"), command=dialog.destroy)
    cancel_btn.pack(side=tk.RIGHT, padx=8, ipady=6, ipadx=12)

    self.root.wait_window(dialog)
    return result[0]

  def add_custom_skin_pack(self):
    rules_msg = (
        "• Choose a folder containing your .iwi / .ff files.\n"
        "• Ensure a preview image (.png) is placed inside\n"
        "  that same folder to display it in the app catalog."
    )
    self.show_modern_info_dialog("CUSTOM PACK GUIDELINES", rules_msg)

    current_cat = [
        cat for cat, btn in self.category_buttons.items()
        if btn.cget("bg") == self.btn_red
    ]
    active_category = current_cat[0] if current_cat else "WEAPONS"

    source_folder = filedialog.askdirectory(title=f"Select Folder Containing .iwi Files for {active_category}")
    if not source_folder:
      return

    pack_name = self.show_modern_input_dialog("PACK IDENTIFIER", "Enter a name for your custom pack folder:")
    if not pack_name:
      return

    safe_folder_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in pack_name).strip().replace(" ", "_")
    target_dir = os.path.join(SKINS_DIR, active_category, safe_folder_name)
    
    try:
      os.makedirs(target_dir, exist_ok=True)
      
      files_in_source = os.listdir(source_folder)
      copied_count = 0
      for file_name in files_in_source:
        src_file = os.path.join(source_folder, file_name)
        if os.path.isfile(src_file):
          shutil.copy2(src_file, target_dir)
          copied_count += 1

      if copied_count == 0:
        messagebox.showwarning("Warning", "The selected folder was empty.")
        return

      self.show_modern_info_dialog("DEPLOYMENT SUCCESS", f"Custom pack '{pack_name}' successfully added\nto Skins/{active_category}/!")
      self.skins_catalog = self.manager.scan_skins_catalog()
      self.load_skin_category(active_category)
    except Exception as e:
      messagebox.showerror("Error", f"Failed to add pack folder: {e}")

  def load_skin_category(self, category_name):
    for name, btn in self.category_buttons.items():
      if name == category_name:
        btn.config(bg=self.btn_red, fg="#ffffff")
      else:
        btn.config(bg=self.bg_input, fg=self.fg_muted)

    for widget in self.skins_display_frame.winfo_children():
      widget.destroy()

    if hasattr(self, "canvas"):
      self.canvas.yview_moveto(0.0)

    self.skin_images = []
    skins_list = self.skins_catalog.get(category_name, [])

    if not skins_list:
      empty_msg = (
          f"// No skin folders found in 'Skins/{category_name.lower()}/'.\n//"
          " Click '[ ADD+ PACK ]' above to choose a folder with your .iwi files!"
      )
      empty_lbl = tk.Label(
          self.skins_display_frame,
          text=empty_msg,
          bg=self.bg_card,
          fg=self.fg_muted,
          font=("Consolas", 10),
          justify=tk.LEFT,
      )
      empty_lbl.pack(anchor="w", pady=15)
      return

    for skin in skins_list:
      card = tk.Frame(
          self.skins_display_frame,
          bg=self.bg_input,
          highlightbackground="#18181b",
          highlightthickness=1,
      )
      card.pack(fill=tk.X, expand=True, padx=5, pady=10)

      img_container = tk.Frame(
          card,
          bg="#000000",
          width=320,
          height=160,
          highlightbackground="#18181b",
          highlightthickness=1,
      )
      img_container.pack(side=tk.LEFT, padx=14, pady=14)
      img_container.pack_propagate(False)

      if skin.get("image_filename"):
        img_path = os.path.join(
            SKINS_DIR, skin["bundle_folder"], skin["image_filename"]
        )
        try:
          pil_img = Image.open(img_path)
          pil_img = pil_img.resize((300, 140), Image.Resampling.LANCZOS)
          photo = ImageTk.PhotoImage(pil_img)
          self.skin_images.append(photo)

          img_lbl = tk.Label(img_container, image=photo, bg="#000000")
          img_lbl.pack(expand=True)
        except Exception:
          fallback_lbl = tk.Label(
              img_container,
              text=f"[ {category_name} ]",
              bg="#000000",
              fg=self.text_red,
              font=("Consolas", 10, "bold"),
          )
          fallback_lbl.pack(expand=True)
      else:
        fallback_lbl = tk.Label(
            img_container,
            text=f"[ {skin['name']} ]",
            bg="#000000",
            fg=self.text_red,
            font=("Consolas", 10, "bold"),
        )
        fallback_lbl.pack(expand=True)

      info_right_frame = tk.Frame(card, bg=self.bg_input)
      info_right_frame.pack(
          side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15), pady=14
      )

      name_lbl = tk.Label(
          info_right_frame,
          text=skin["name"],
          bg=self.bg_input,
          fg=self.text_red,
          font=("Consolas", 12, "bold"),
      )
      name_lbl.pack(anchor="w", pady=(2, 2))

      type_lbl = tk.Label(
          info_right_frame,
          text=skin["type"],
          bg=self.bg_input,
          fg=self.fg_muted,
          font=("Consolas", 9),
      )
      type_lbl.pack(anchor="w", pady=(0, 15))

      if category_name == "BACKGROUNDS":
        is_installed = os.path.exists(
            os.path.join(PLUTONIUM_T6_IMAGES_DIR, "lui_bkg_zm.iwi")
        )
      else:
        is_installed = all(
            os.path.exists(os.path.join(PLUTONIUM_T6_IMAGES_DIR, f))
            for f in skin["iwi_filenames"]
        )

      if is_installed:
        btn_text = "[ ✓ ACTIVE / INSTALLED ]"
        btn_bg = self.btn_green
        btn_hover = self.btn_green_hover
      else:
        btn_text = "[ ✗ APPLY SKIN ]"
        btn_bg = self.btn_red
        btn_hover = self.btn_hover

      apply_btn = tk.Button(
          info_right_frame,
          text=btn_text,
          bg=btn_bg,
          fg="#ffffff",
          activebackground=btn_hover,
          activeforeground="#ffffff",
          bd=0,
          font=("Consolas", 9, "bold"),
          command=lambda s=skin, c=category_name: self.toggle_skin_file(s, c),
      )
      apply_btn.pack(anchor="w", fill=tk.X, ipady=8)

  def toggle_skin_file(self, skin_data, category_name):
    try:
      os.makedirs(PLUTONIUM_T6_IMAGES_DIR, exist_ok=True)

      if category_name == "BACKGROUNDS":
        target_file_name = "lui_bkg_zm.iwi"
        target_path = os.path.join(PLUTONIUM_T6_IMAGES_DIR, target_file_name)

        if os.path.exists(target_path):
          os.remove(target_path)
        else:
          source_file = os.path.join(
              SKINS_DIR, skin_data["bundle_folder"], skin_data["iwi_filenames"][0]
          )
          if not os.path.exists(source_file):
            messagebox.showerror(
                "Error", "Could not find .iwi file for background."
            )
            return
          shutil.copy2(source_file, target_path)
      else:
        all_installed = all(
            os.path.exists(os.path.join(PLUTONIUM_T6_IMAGES_DIR, f))
            for f in skin_data["iwi_filenames"]
        )

        for iwi_file in skin_data["iwi_filenames"]:
          source_file = os.path.join(SKINS_DIR, skin_data["bundle_folder"], iwi_file)
          target_path = os.path.join(PLUTONIUM_T6_IMAGES_DIR, iwi_file)

          if all_installed:
            if os.path.exists(target_path):
              os.remove(target_path)
          else:
            if os.path.exists(source_file):
              shutil.copy2(source_file, target_path)

      self.load_skin_category(category_name)
    except Exception as e:
      messagebox.showerror("Error", str(e))

  def remove_all_current_category(self):
    current_cat = [
        cat
        for cat, btn in self.category_buttons.items()
        if btn.cget("bg") == self.btn_red
    ]
    if not current_cat:
      return
    cat_name = current_cat[0]
    skins_list = self.skins_catalog.get(cat_name, [])

    try:
      for skin in skins_list:
        if cat_name == "BACKGROUNDS":
          target_path = os.path.join(PLUTONIUM_T6_IMAGES_DIR, "lui_bkg_zm.iwi")
          if os.path.exists(target_path):
            os.remove(target_path)
        else:
          for iwi_file in skin["iwi_filenames"]:
            target_path = os.path.join(PLUTONIUM_T6_IMAGES_DIR, iwi_file)
            if os.path.exists(target_path):
              os.remove(target_path)

      self.load_skin_category(cat_name)
    except Exception as e:
      messagebox.showerror("Error", str(e))

  def build_settings_panel(self):
    lbl = tk.Label(
        self.content_card,
        text="C:\\> system_configuration --path & socials",
        bg=self.bg_card,
        fg=self.text_red,
        font=("Consolas", 10, "bold"),
    )
    lbl.pack(anchor="w", padx=18, pady=(15, 8))

    path_box = tk.Frame(self.content_card, bg=self.bg_input)
    path_box.pack(fill=tk.X, padx=18, pady=10)

    self.path_lbl = tk.Label(
        path_box,
        text=f"Directory: {self.manager.get_game_path() or 'Not Linked'}",
        bg=self.bg_input,
        fg=self.text_red,
        font=("Consolas", 9),
    )
    self.path_lbl.pack(side=tk.LEFT, padx=12, pady=14)

    change_btn = tk.Button(
        path_box,
        text="CHANGE",
        bg=self.bg_card,
        fg=self.text_red,
        activebackground=self.btn_red,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 9, "bold"),
        command=self.change_game_path,
        padx=12,
    )
    change_btn.pack(side=tk.RIGHT, padx=10, pady=10)

    socials_frame = tk.Frame(
        self.content_card,
        bg=self.bg_input,
        highlightbackground="#18181b",
        highlightthickness=1,
    )
    socials_frame.pack(fill=tk.X, padx=18, pady=10)

    soc_title = tk.Label(
        socials_frame,
        text="[ DEVELOPER CONTACT & LINKS ]",
        bg=self.bg_input,
        fg=self.text_red,
        font=("Consolas", 9, "bold"),
    )
    soc_title.pack(anchor="w", padx=12, pady=(10, 5))

    btn_row = tk.Frame(socials_frame, bg=self.bg_input)
    btn_row.pack(anchor="w", padx=12, pady=(0, 6))

    disc_btn = tk.Button(
        btn_row,
        text="[ Discord: kadidxd ]",
        bg=self.bg_card,
        fg=self.text_red,
        activebackground=self.btn_red,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 8, "bold"),
        command=lambda: self.open_link("https://discord.com"),
    )
    disc_btn.pack(side=tk.LEFT, padx=(0, 8), ipady=5, ipadx=8)

    insta_btn = tk.Button(
        btn_row,
        text="[ Instagram ]",
        bg=self.bg_card,
        fg=self.text_red,
        activebackground=self.btn_red,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 8, "bold"),
        command=lambda: self.open_link("https://www.instagram.com/abdo1o_x_toxic/"),
    )
    insta_btn.pack(side=tk.LEFT, padx=(0, 8), ipady=5, ipadx=8)

    gh_btn = tk.Button(
        btn_row,
        text="[ GitHub ]",
        bg=self.bg_card,
        fg=self.text_red,
        activebackground=self.btn_red,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 8, "bold"),
        command=lambda: self.open_link("https://github.com/abdousaci217"),
    )
    gh_btn.pack(side=tk.LEFT, ipady=5, ipadx=8)

    donate_row = tk.Frame(socials_frame, bg=self.bg_input)
    donate_row.pack(fill=tk.X, padx=12, pady=(0, 12))

    donate_lbl = tk.Label(
        donate_row,
        text="Want to support my work? Donate via USDT (TRC20): TX7bxQXyyomx7dRxt6cxxjAmyps7QAx7b4",
        bg=self.bg_input,
        fg=self.fg_muted,
        font=("Consolas", 8),
    )
    donate_lbl.pack(side=tk.LEFT)

    copy_donate_btn = tk.Button(
        donate_row,
        text="[ COPY WALLET ]",
        bg=self.bg_card,
        fg=self.text_red,
        activebackground=self.btn_red,
        activeforeground="#ffffff",
        bd=0,
        font=("Consolas", 8, "bold"),
        command=lambda: self.copy_to_clipboard("TX7bxQXyyomx7dRxt6cxxjAmyps7QAx7b4"),
    )
    copy_donate_btn.pack(side=tk.LEFT, padx=10, ipady=2)

    info = tk.Label(
        self.content_card,
        text=f"{APP_NAME} v6.2 — Ready For Release Edition",
        bg=self.bg_card,
        fg=self.fg_muted,
        font=("Consolas", 8),
    )
    info.pack(anchor="w", padx=18, pady=10)

  def copy_to_clipboard(self, text):
    self.root.clipboard_clear()
    self.root.clipboard_append(text)
    messagebox.showinfo("Copied", "USDT TRC20 address copied to clipboard!")

  def open_link(self, url):
    try:
      import webbrowser
      webbrowser.open(url)
    except Exception:
      pass

  def check_first_run(self):
    if not self.manager.get_game_path() or not self.manager.validate_game_path(
        self.manager.get_game_path()
    ):
      messagebox.showinfo(
          APP_NAME,
          "Terminal initialization required: Link your Black Ops 2 folder.",
      )
      self.change_game_path()

  def change_game_path(self):
    path = filedialog.askdirectory(title="Select Black Ops 2 Directory")
    if path:
      if self.manager.validate_game_path(path):
        self.manager.config["game_path"] = path
        self.manager.save_config()
        if hasattr(self, "path_lbl"):
          self.path_lbl.config(text=f"Directory: {path}")
        messagebox.showinfo("Success", "Game path bound successfully!")
      else:
        messagebox.showerror(
            "Error", "Invalid path! t6mp.exe / t6zm.exe not detected."
        )

  def browse_mod_file(self):
    file = filedialog.askopenfilename(
        filetypes=[
            ("Scripts & Textures", "*.gsc;*.csc;*.ff;*.iwi"),
            ("All Files", "*.*"),
        ]
    )
    if file:
      self.mod_entry.delete(0, tk.END)
      self.mod_entry.origin = file
      self.mod_entry.insert(0, file)

  def install_mod_action(self):
    src = self.mod_entry.get()
    if not src:
      messagebox.showwarning("Warning", "Provide a file path first.")
      return
    try:
      name = self.manager.install_file(src)
      self.log_msg(f"[SUCCESS] Deployed payload -> {name}")
      messagebox.showinfo(
          "Success", f"{name} successfully installed into Plutonium storage!"
      )
      self.mod_entry.delete(0, tk.END)
    except Exception as e:
      messagebox.showerror("Error", str(e))

  def log_msg(self, text):
    if hasattr(self, "log_box"):
      self.log_box.config(state="normal")
      self.log_box.insert(tk.END, text + "\n")
      self.log_box.see(tk.END)
      self.log_box.config(state="disabled")


if __name__ == "__main__":
  root = tk.Tk()
  app = KadixClientGUI(root)
  root.mainloop()