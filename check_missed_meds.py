#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from datetime import datetime, time

def load_log():
    log_file = os.path.expanduser("~/med_log.json")
    try:
        with open(log_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def show_notification(message, urgency="critical"):
    try:
        subprocess.run([
            'notify-send', 
            '-u', urgency,
            '-t', '0',  # Persistent notification
            '-i', 'dialog-warning',
            'MISSED MEDICATION!', 
            message
        ], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"*** MISSED MEDICATION: {message} ***")

def check_missed_medications():
    current_time = datetime.now().time()
    today_key = datetime.now().strftime("%Y-%m-%d")
    log = load_log()
    
    today_log = log.get(today_key, {})
    
    # Check morning meds (should be taken by 10 AM if it's after 8 AM)
    if current_time >= time(8, 0) and current_time <= time(23, 59):
        if 'morning' not in today_log:
            show_notification(
                "⚠️ MORNING MEDICATION MISSED!\n\n"
                "• Elvanse 20mg\n"
                "• Escitalopram 5mg\n"
                "• Dexamfetamine 5mg\n\n"
                "Click to take them now!",
                "critical"
            )
            # Run morning reminder
            subprocess.Popen([sys.executable, os.path.expanduser("~/med_reminder.py"), "morning"])
    
    # Check afternoon meds (should be taken by 18:00 if it's after 16:30)
    if current_time >= time(16, 30) and current_time <= time(23, 59):
        if 'afternoon' not in today_log:
            show_notification(
                "⚠️ AFTERNOON MEDICATION MISSED!\n\n"
                "• Dexamfetamine 5mg\n\n"
                "Click to take it now!",
                "critical"
            )
            # Run afternoon reminder
            subprocess.Popen([sys.executable, os.path.expanduser("~/med_reminder.py"), "afternoon"])

if __name__ == "__main__":
    check_missed_medications()