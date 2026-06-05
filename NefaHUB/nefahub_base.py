import ctypes
import tkinter as tk
import nefahub_config
import nefahub_core

if __name__ == "__main__":
    try:   ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass

    root = tk.Tk()
    app = nefahub_core.NefaHUBApp(root, config=nefahub_config.BaseConfig())
    root.mainloop()
