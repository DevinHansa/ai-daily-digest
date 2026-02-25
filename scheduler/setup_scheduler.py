"""
scheduler/setup_scheduler.py — Registers a Windows Task Scheduler job to run
the AI News Digest every day at 7:30 AM Sri Lanka time (local clock).

Run this ONCE to set up the schedule:
    python scheduler/setup_scheduler.py

To remove the task:
    python scheduler/setup_scheduler.py --remove
"""

import os
import sys
import subprocess
import argparse

TASK_NAME = "AI_News_Digest_Daily"
SCHEDULE_TIME = "07:30"   # 7:30 AM — local time (keep your PC clock in SLT)


def get_python_exe() -> str:
    """Return the absolute path to the current Python executable."""
    return sys.executable


def get_script_path() -> str:
    """Return the absolute path to run_digest.py."""
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "run_digest.py")
    )


def register_task():
    python_exe  = get_python_exe()
    script_path = get_script_path()
    working_dir = os.path.dirname(script_path)

    print(f"  Python   : {python_exe}")
    print(f"  Script   : {script_path}")
    print(f"  Work dir : {working_dir}")
    print(f"  Schedule : daily at {SCHEDULE_TIME}")
    print()

    # Use schtasks to create the task
    cmd = [
        "schtasks", "/Create",
        "/F",                          # Force overwrite if exists
        "/TN", TASK_NAME,
        "/TR", f'"{python_exe}" "{script_path}"',
        "/SC", "DAILY",
        "/ST", SCHEDULE_TIME,
        "/SD", "01/01/2025",           # Start date (past date = immediate)
        "/RL", "HIGHEST",              # Run with highest privileges
        "/IT",                         # Run only when user is logged in
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, shell=False)

    if result.returncode == 0:
        print("✅ Task registered successfully!")
        print(f"   Task name : {TASK_NAME}")
        print(f"   Runs at   : {SCHEDULE_TIME} daily (use your PC in SL timezone)")
        print()
        print("📋 To verify, open Windows Task Scheduler and look for:")
        print(f"   Task Scheduler Library > {TASK_NAME}")
    else:
        print(f"❌ Failed to register task:")
        print(result.stderr or result.stdout)
        print()
        print("💡 Try running this script as Administrator (right-click → Run as Admin)")


def remove_task():
    cmd = ["schtasks", "/Delete", "/F", "/TN", TASK_NAME]
    result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if result.returncode == 0:
        print(f"✅ Task '{TASK_NAME}' removed.")
    else:
        print(f"❌ Could not remove task: {result.stderr or result.stdout}")


def show_status():
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"]
    result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Task '{TASK_NAME}' not found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Windows Task Scheduler setup for AI Digest")
    parser.add_argument("--remove", action="store_true", help="Remove the scheduled task")
    parser.add_argument("--status", action="store_true", help="Show current task status")
    args = parser.parse_args()

    print("⏰  AI News Digest — Windows Task Scheduler")
    print("─" * 50)

    if args.remove:
        remove_task()
    elif args.status:
        show_status()
    else:
        register_task()
