import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "NefaHUB"))
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
    app = nefahub_core.NefaHUBApp(root, config=nefahub_config.ModernConfig())
    root.mainloop()
