import tkinter as tk
import sys
import time
from screeninfo import get_monitors

def get_monitor_geometry(monitor_index):
    try:
        monitors = get_monitors()
        if monitor_index < len(monitors):
            m = monitors[monitor_index]
            return f"{m.width}x{m.height}+{m.x}+{m.y}", m
        else:
            print(f"Error: Monitor index {monitor_index} out of range (Found {len(monitors)} monitors).")
            return None, None
    except Exception as e:
        print(f"Error getting monitors: {e}")
        return None, None

def test_method_1(geometry, root):
    print(f"\n[Method 1] Current Approach: overrideredirect toggle")
    print(f"Target Geometry: {geometry}")
    
    window = tk.Toplevel(root)
    window.title("Method 1")
    window.configure(bg="red")
    
    label = tk.Label(window, text="Method 1: Current Approach\n(Red Background)", font=("Arial", 24), fg="white", bg="red")
    label.pack(expand=True)
    
    # The 'Current' logic from main.py
    window.overrideredirect(False)
    window.geometry(geometry)
    window.update()
    window.overrideredirect(True)
    
    return window

def test_method_2(geometry, root):
    print(f"\n[Method 2] overrideredirect FIRST")
    print(f"Target Geometry: {geometry}")
    
    window = tk.Toplevel(root)
    window.title("Method 2")
    window.configure(bg="blue")
    
    label = tk.Label(window, text="Method 2: overrideredirect FIRST\n(Blue Background)", font=("Arial", 24), fg="white", bg="blue")
    label.pack(expand=True)
    
    window.overrideredirect(True)
    window.geometry(geometry)
    
    # Linux specific: sometimes need to wait for visibility before mapping takes effect?
    # window.wait_visibility(window) 
    
    return window

def test_method_3(geometry, root, monitor):
    print(f"\n[Method 3] Fullscreen Attribute")
    print(f"Target Geometry: {geometry}")
    
    window = tk.Toplevel(root)
    window.title("Method 3")
    window.configure(bg="green")
    
    label = tk.Label(window, text="Method 3: Fullscreen Attribute\n(Green Background)", font=("Arial", 24), fg="white", bg="green")
    label.pack(expand=True)
    
    # Position it roughly first
    window.geometry(f"{monitor.x}+{monitor.y}")
    window.overrideredirect(False) # Fullscreen usually manages decorations
    window.attributes('-fullscreen', True)
    
    return window

def main():
    root = tk.Tk()
    root.withdraw() # Hide main window

    monitors = get_monitors()
    print(f"Detected {len(monitors)} monitors.")
    for i, m in enumerate(monitors):
        print(f"  {i}: {m}")

    if len(monitors) < 2:
        print("Warning: Only 1 monitor detected. Tests will run on primary.")
        target_idx = 0
    else:
        # Default to the first non-primary or just index 1
        target_idx = 1
        for i, m in enumerate(monitors):
            if not m.is_primary:
                target_idx = i
                break
    
    print(f"\nTargeting Monitor {target_idx}")
    geometry, monitor = get_monitor_geometry(target_idx)
    
    if not geometry:
        return

    print("\nStarting tests... Press ENTER in the terminal to cycle through tests.")
    
    # Test 1
    input("Press Enter to run Method 1 (Red)...")
    w1 = test_method_1(geometry, root)
    print("Window 1 launched.")
    input("Press Enter to close Method 1 and try Method 2...")
    w1.destroy()
    root.update()

    # Test 2
    input("Press Enter to run Method 2 (Blue)...")
    w2 = test_method_2(geometry, root)
    print("Window 2 launched.")
    input("Press Enter to close Method 2 and try Method 3...")
    w2.destroy()
    root.update()

    # Test 3
    input("Press Enter to run Method 3 (Green)...")
    w3 = test_method_3(geometry, root, monitor)
    print("Window 3 launched.")
    input("Press Enter to close Method 3 and Exit...")
    w3.destroy()
    
    print("Done.")
    root.destroy()

if __name__ == "__main__":
    main()
