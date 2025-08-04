#!/usr/bin/env python3
import time
import subprocess
import os
import sys
from datetime import datetime
import json
import tkinter as tk
from tkinter import messagebox, ttk
import threading

class MedReminder:
    def __init__(self, reminder_type="morning"):
        self.reminder_type = reminder_type
        self.sound_stop_event = threading.Event()
        
        if reminder_type == "morning":
            self.medicines = [
                "Elvanse 20mg",
                "Escitalopram 5mg", 
                "Dexamfetamine 5mg"
            ]
            self.reminder_title = "🌅 MORNING MEDICATION TIME!"
        elif reminder_type == "afternoon":
            self.medicines = [
                "Dexamfetamine 5mg (afternoon dose)"
            ]
            self.reminder_title = "🌆 AFTERNOON MEDICATION TIME!"
        
        self.log_file = os.path.expanduser("~/med_log.json")
        self.reminder_count = 0
        self.max_reminders = 10
        
    def get_today_key(self):
        now = datetime.now()
        # If it's before 8 AM, consider it part of the previous medication day
        if now.hour < 8:
            # Subtract one day to get the previous medication day
            from datetime import timedelta
            yesterday = now - timedelta(days=1)
            return yesterday.strftime("%Y-%m-%d")
        else:
            return now.strftime("%Y-%m-%d")
    
    def load_log(self):
        try:
            with open(self.log_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_log(self, taken_meds):
        log = self.load_log()
        today_key = self.get_today_key()
        
        if today_key not in log:
            log[today_key] = {}
        
        log[today_key][self.reminder_type] = {
            'medicines': taken_meds,
            'time_taken': datetime.now().isoformat(),
            'reminder_count': self.reminder_count
        }
        
        with open(self.log_file, 'w') as f:
            json.dump(log, f, indent=2)
    
    def already_taken_today(self):
        log = self.load_log()
        today = self.get_today_key()
        return (today in log and 
                self.reminder_type in log[today] and 
                len(log[today][self.reminder_type].get('medicines', [])) == len(self.medicines))
    
    def show_desktop_notification(self, urgency="normal"):
        message = f"🏥 MEDICATION TIME!\n\n" + "\n".join([f"• {med}" for med in self.medicines])
        try:
            subprocess.run([
                'notify-send', 
                '-u', urgency,
                '-t', '30000' if urgency == 'critical' else '10000',
                '-i', 'dialog-warning',
                'Medication Reminder', 
                message
            ], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Desktop notifications not available - showing console message")
            print(f"*** {message} ***")
    
    def stop_sound(self):
        """Stop any currently playing sounds"""
        self.sound_stop_event.set()
    
    def play_alarm_sound(self, urgency_level=1):
        # Reset the stop event
        self.sound_stop_event.clear()
        
        # Your chosen sound
        sounds = ["/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"]
        
        # Alarm-like repetition pattern
        if urgency_level <= 1:
            repetitions = 3
            interval = 0.5
        elif urgency_level <= 3:
            repetitions = 5
            interval = 0.4
        else:
            repetitions = 8
            interval = 0.3
        
        def play_sound_async():
            for sound in sounds:
                if os.path.exists(sound):
                    try:
                        # Play sound with gentle repetitions, checking for stop signal
                        for i in range(repetitions):
                            if self.sound_stop_event.is_set():
                                return  # Stop immediately if requested
                            
                            subprocess.run(['paplay', sound], check=False, 
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            
                            # Check again before sleeping
                            if i < repetitions - 1 and not self.sound_stop_event.is_set():
                                time.sleep(interval)
                        return
                    except FileNotFoundError:
                        # Try aplay as backup
                        try:
                            for i in range(repetitions):
                                if self.sound_stop_event.is_set():
                                    return
                                
                                subprocess.run(['aplay', sound], check=False,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                
                                if i < repetitions - 1 and not self.sound_stop_event.is_set():
                                    time.sleep(interval)
                            return
                        except FileNotFoundError:
                            continue
            
            # Very gentle fallback beep
            if not self.sound_stop_event.is_set():
                print("\a")
        
        # Play sound in a separate thread to not block GUI
        sound_thread = threading.Thread(target=play_sound_async, daemon=True)
        sound_thread.start()
    
    def show_gui_reminder(self):
        completed = [False]  # Use list to allow modification in nested function
        
        def on_taken():
            # Stop sound immediately when user clicks
            self.stop_sound()
            
            selected = []
            for i, var in enumerate(med_vars):
                if var.get():
                    selected.append(self.medicines[i])
            
            if len(selected) == len(self.medicines):
                self.save_log(selected)
                messagebox.showinfo("Success", "🎉 Great! All medications logged.\nSee you next time!")
                completed[0] = True
                root.destroy()
            else:
                messagebox.showwarning("Incomplete", f"⚠️ Please check all {len(self.medicines)} medications")
        
        def on_snooze():
            # Stop sound when snoozing
            self.stop_sound()
            root.destroy()
        
        def on_window_focus(event=None):
            # Play gentler sound when window gains focus (only if no sound is playing)
            if self.sound_stop_event.is_set() or not hasattr(self, '_initial_sound_played'):
                self.play_alarm_sound(max(1, self.reminder_count))
            
        root = tk.Tk()
        root.title("💊 Medication Reminder")
        root.geometry("500x400")
        root.attributes('-topmost', True)
        root.attributes('-fullscreen', False)
        root.resizable(False, False)
        
        # Color scheme based on urgency
        if self.reminder_count > 3:
            bg_color = '#ff4444'  # Red
            accent_color = '#cc0000'
            text_color = 'white'
        elif self.reminder_count > 1:
            bg_color = '#ff8800'  # Orange
            accent_color = '#cc6600'
            text_color = 'white'
        else:
            bg_color = '#4a90e2'  # Blue
            accent_color = '#357abd'
            text_color = 'white'
        
        root.configure(bg=bg_color)
        
        # Custom style for this urgency level
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure('Custom.TFrame', background=bg_color)
        style.configure('Title.TLabel', background=bg_color, foreground=text_color, 
                       font=('Ubuntu', 18, 'bold'))
        style.configure('Subtitle.TLabel', background=bg_color, foreground=text_color,
                       font=('Ubuntu', 12))
        style.configure('Med.TCheckbutton', background=bg_color, foreground=text_color,
                       font=('Ubuntu', 11), focuscolor='none')
        style.configure('Action.TButton', font=('Ubuntu', 11, 'bold'))
        
        main_frame = ttk.Frame(root, style='Custom.TFrame', padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header section
        header_frame = ttk.Frame(main_frame, style='Custom.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text=self.reminder_title, 
                               style='Title.TLabel')
        title_label.pack()
        
        current_time = datetime.now().strftime("%H:%M")
        time_label = ttk.Label(header_frame, 
                              text=f"Reminder #{self.reminder_count + 1} • {current_time}", 
                              style='Subtitle.TLabel')
        time_label.pack(pady=(5, 0))
        
        # Medications section
        med_frame = ttk.Frame(main_frame, style='Custom.TFrame')
        med_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        med_title = ttk.Label(med_frame, text="📋 Please check off each medication:", 
                             style='Subtitle.TLabel')
        med_title.pack(anchor='w', pady=(0, 15))
        
        med_vars = []
        for i, med in enumerate(self.medicines):
            var = tk.BooleanVar()
            med_vars.append(var)
            
            med_container = ttk.Frame(med_frame, style='Custom.TFrame')
            med_container.pack(fill=tk.X, pady=8)
            
            # Add pill emoji based on medication type
            pill_emoji = "💊" if "mg" in med else "💉"
            cb = ttk.Checkbutton(med_container, 
                               text=f"{pill_emoji} {med}", 
                               variable=var, 
                               style='Med.TCheckbutton')
            cb.pack(anchor='w', padx=20)
        
        # Button section
        button_frame = ttk.Frame(main_frame, style='Custom.TFrame')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Style buttons based on urgency
        taken_btn = ttk.Button(button_frame, text="✅ All Taken!", 
                              command=on_taken, style='Action.TButton')
        taken_btn.pack(side=tk.LEFT, padx=(0, 10), ipadx=20, ipady=10)
        
        snooze_btn = ttk.Button(button_frame, text="😴 Snooze 5min", 
                               command=on_snooze, style='Action.TButton')
        snooze_btn.pack(side=tk.RIGHT, padx=(10, 0), ipadx=20, ipady=10)
        
        # Center the window on screen
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f"+{x}+{y}")
        
        # Enhanced GNOME context handling - ensure window appears on all workspaces
        try:
            # Set window to appear on all workspaces
            root.attributes('-type', 'dialog')
            # Force window to be always on top and visible
            root.attributes('-topmost', True)
            root.wm_attributes('-type', 'dialog')
        except tk.TclError:
            pass  # Fallback for systems that don't support these attributes
        
        # Auto-focus and bring to front with enhanced GNOME handling
        root.focus_force()
        root.lift()
        root.after_idle(lambda: root.focus_force())
        root.after_idle(lambda: root.lift())
        
        # Send urgent notification to ensure GNOME shows it
        try:
            subprocess.run([
                'notify-send', 
                '-u', 'critical',
                '-t', '0',  # Don't auto-dismiss
                '-i', 'dialog-warning',
                'MEDICATION REMINDER WINDOW OPEN',
                'Please check your medication reminder window!'
            ], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass
        
        # Play initial gentle sound
        self._initial_sound_played = True
        root.after(100, lambda: self.play_alarm_sound(max(1, self.reminder_count)))
        
        # Bind focus events for gentle sound alerts
        root.bind('<FocusIn>', on_window_focus)
        
        # Stop sound when window is closed
        def on_closing():
            self.stop_sound()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        try:
            root.mainloop()
            return completed[0]  # Return True if medications were taken
        except tk.TclError:
            return False
    
    def run_reminder_cycle(self):
        if self.already_taken_today():
            print("Medications already taken today!")
            return
        
        print(f"Starting medication reminder cycle...")
        
        while self.reminder_count < self.max_reminders:
            # Check if medications were taken while script was running
            if self.already_taken_today():
                print("Medications were taken - stopping reminders!")
                return
                
            print(f"Reminder #{self.reminder_count + 1}")
            
            # Show notifications with increasing urgency
            if self.reminder_count == 0:
                self.show_desktop_notification("normal")
            elif self.reminder_count < 3:
                self.show_desktop_notification("normal")
            else:
                self.show_desktop_notification("critical")
            
            # Show GUI - this blocks until user responds
            if self.show_gui_reminder():
                print("Medications taken successfully!")
                return
            
            self.reminder_count += 1
            
            # Wait between reminders (shorter intervals as urgency increases)
            if self.reminder_count < 3:
                wait_time = 300  # 5 minutes
            elif self.reminder_count < 6:
                wait_time = 180  # 3 minutes  
            else:
                wait_time = 60   # 1 minute
                
            print(f"Waiting {wait_time//60} minutes before next reminder...")
            time.sleep(wait_time)
        
        print("Maximum reminders reached. Please take your medication!")

if __name__ == "__main__":
    reminder_type = "morning"  # default
    if len(sys.argv) > 1:
        reminder_type = sys.argv[1]
    
    reminder = MedReminder(reminder_type)
    reminder.run_reminder_cycle()