import cv2
import numpy as np
import pyautogui
import datetime
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from threading import Thread
import os


# ======================================================================
# CONFIGURATION
# ======================================================================
FPS_REQUEST = 20.0
CODEC = cv2.VideoWriter_fourcc(*"MJPG")    # ✔ 100% stable Windows codec
EXTENSION = ".avi"                         # ✔ stable container
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
RESOLUTION = (SCREEN_WIDTH, SCREEN_HEIGHT)


# ======================================================================
# GLOBAL STATE
# ======================================================================
recording_state = 0         # 0=stopped, 1=recording, 2=paused
out = None
current_temp_filename = None
thread_running = False
actual_fps = FPS_REQUEST
fps_ready = False

write_enabled = False       # ✔ prevents crashes on stop


# ======================================================================
# FPS CONTROLLER
# ======================================================================
class FrameRateController:
    def __init__(self, fps):
        self.target_interval = 1.0 / fps
        self.start_time = time.time()
        self.frame_count = 0

    def wait(self):
        self.frame_count += 1
        ideal_end = self.start_time + self.frame_count * self.target_interval
        sleep = ideal_end - time.time()
        if sleep > 0:
            time.sleep(sleep)


def get_unique_filename():
    return f"temp_record_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{EXTENSION}"


# ======================================================================
# FILE EXPORT
# ======================================================================
def prompt_for_save_location():
    global current_temp_filename

    if not current_temp_filename or not os.path.exists(current_temp_filename):
        messagebox.showinfo("Export Error", "No recorded file found.")
        return

    initial_save = current_temp_filename.replace("temp_", "")

    final_path = filedialog.asksaveasfilename(
        defaultextension=EXTENSION,
        initialfile=initial_save,
        filetypes=[("AVI video files", "*.avi"), ("All files", "*.*")],
        title="Save Recorded Video",
    )

    if final_path:
        try:
            os.rename(current_temp_filename, final_path)
            messagebox.showinfo("Export Successful", f"Saved:\n{final_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
        finally:
            current_temp_filename = None
    else:
        messagebox.showinfo("Canceled", f"Temp file kept:\n{current_temp_filename}")


# ======================================================================
# BUTTON LOGIC
# ======================================================================
def start_or_resume_recording():
    global out, recording_state, current_temp_filename, actual_fps, fps_ready, write_enabled

    if not fps_ready:
        messagebox.showinfo("Please wait", "Measuring FPS… Try again in 2 seconds.")
        return

    if recording_state == 0:

        current_temp_filename = get_unique_filename()

        # ✔ Create writer with measured FPS
        out = cv2.VideoWriter(current_temp_filename, CODEC, actual_fps, RESOLUTION)

        write_enabled = True
        recording_state = 1
        update_gui_status("Recording...", "red")

    elif recording_state == 2:
        write_enabled = True
        recording_state = 1
        update_gui_status("Recording...", "red")

    update_button_states()


def pause_recording():
    global recording_state, write_enabled
    if recording_state == 1:
        write_enabled = False      # ✔ stop writing immediately
        recording_state = 2
        update_gui_status("Paused", "orange")
        update_button_states()


def stop_recording():
    global out, recording_state, write_enabled

    write_enabled = False  # ✔ stop writing immediately

    time.sleep(0.05)       # ✔ allow capture thread to finish current frame

    if recording_state in (1, 2):
        if out:
            out.release()

        out = None
        recording_state = 0
        update_gui_status("Stopped (Ready to Export)", "blue")
        update_button_states()


def export_and_exit():
    global thread_running, current_temp_filename

    stop_recording()

    if current_temp_filename and os.path.exists(current_temp_filename):
        if messagebox.askyesno("Export Recording", "Export recorded video?"):
            prompt_for_save_location()

        if current_temp_filename and os.path.exists(current_temp_filename):
            os.remove(current_temp_filename)

    thread_running = False
    root.quit()


# ======================================================================
# GUI UTILITY
# ======================================================================
def update_gui_status(text, color):
    status_label.config(text=f"Status: {text}", foreground=color)


def update_button_states():
    if recording_state == 0:
        start_button.config(state=tk.NORMAL)
        pause_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.DISABLED)
    elif recording_state == 1:
        start_button.config(state=tk.DISABLED)
        pause_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.NORMAL)
    elif recording_state == 2:
        start_button.config(state=tk.NORMAL)
        pause_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)


# ======================================================================
# VIDEO CAPTURE THREAD (CRASH-PROOF)
# ======================================================================
def video_capture_thread():
    global recording_state, thread_running, actual_fps, fps_ready, out, write_enabled

    thread_running = True
    frame_controller = FrameRateController(FPS_REQUEST)

    # FPS measurement
    frame_counter = 0
    last_time = time.time()

    # Preview size
    preview_scale = 25
    p_w = int(SCREEN_WIDTH * preview_scale / 100)
    p_h = int(SCREEN_HEIGHT * preview_scale / 100)

    while thread_running:

        # Capture screenshot
        img = pyautogui.screenshot()
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # FPS measurement every 20 frames
        frame_counter += 1
        if frame_counter >= 20:
            now = time.time()
            elapsed = now - last_time
            if elapsed > 0:
                actual_fps = frame_counter / elapsed
            fps_ready = True
            frame_counter = 0
            last_time = now

        # ==================================================================
        # SAFE FRAME WRITING (Crash-proof)
        # ==================================================================
        if write_enabled and out is not None:
            try:
                out.write(frame)
            except Exception as e:
                print("WRITE ERROR (ignored):", e)
                write_enabled = False  # stop writing safely

        # Preview window
        preview = cv2.resize(frame, (p_w, p_h))
        cv2.putText(
            preview,
            {0: "STOPPED", 1: "RECORDING", 2: "PAUSED"}[recording_state],
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255) if recording_state == 1 else (0, 255, 0),
            2,
        )

        cv2.imshow("Recording Preview", preview)

        if cv2.waitKey(1) & 0xFF == 27:
            root.after(0, export_and_exit)
            break

        frame_controller.wait()

    cv2.destroyAllWindows()


# ======================================================================
# GUI SETUP
# ======================================================================
root = tk.Tk()
root.title("Screen Recorder (AVI Stable Edition)")

capture_thread = Thread(target=video_capture_thread, daemon=True)
capture_thread.start()

status_label = ttk.Label(root, text="Status: Stopped",
                         font=("Arial", 14, "bold"), foreground="green")
status_label.pack(pady=10)

frame = ttk.Frame(root)
frame.pack()

start_button = ttk.Button(frame, text="START", command=start_or_resume_recording, width=15)
start_button.grid(row=0, column=0, padx=5, pady=5)

pause_button = ttk.Button(frame, text="PAUSE", command=pause_recording, width=15)
pause_button.grid(row=0, column=1, padx=5, pady=5)

stop_button = ttk.Button(frame, text="STOP", command=stop_recording, width=15)
stop_button.grid(row=1, column=0, padx=5, pady=5)

export_button = ttk.Button(frame, text="EXPORT / EXIT",
                           command=export_and_exit, width=15)
export_button.grid(row=1, column=1, padx=5, pady=5)

update_button_states()

root.protocol("WM_DELETE_WINDOW", export_and_exit)
root.mainloop()
