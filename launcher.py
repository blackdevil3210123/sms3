#!/usr/bin/env python3
"""
24x7 Launcher for SMS Blast Bot.
- Kills ALL existing main.py instances BEFORE starting (prevents conflicts).
- Restarts automatically if the bot crashes.
- NEVER runs more than ONE main.py instance at a time.
"""
import subprocess, os, signal, time, sys

BOT_SCRIPT = "/app/main.py"
LOG_FILE = "/app/bot.log"
MAX_RESTARTS = 100000

def kill_all_bots():
    out = subprocess.run(["pgrep", "-f", "python.*main.py"], capture_output=True, text=True)
    pids = [p.strip() for p in out.stdout.split() if p.strip()]
    for pid in pids:
        try:
            pid_int = int(pid)
            if pid_int == os.getpid():
                continue
            os.kill(pid_int, signal.SIGKILL)
            print(f"[LAUNCHER] Killed stale bot PID {pid_int}")
        except Exception as e:
            print(f"[LAUNCHER] Could not kill {pid}: {e}")
    if pids:
        time.sleep(3)

def start_bot():
    try:
        open(LOG_FILE, "w").close()
    except Exception:
        pass
    proc = subprocess.Popen(
        [sys.executable, BOT_SCRIPT],
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
        cwd="/app",
        start_new_session=True,
    )
    print(f"[LAUNCHER] Started bot PID {proc.pid}")
    return proc

def main():
    print("[LAUNCHER] SMS Blast Bot 24x7 Launcher starting...")
    while True:
        kill_all_bots()
        proc = start_bot()
        rc = proc.wait()
        print(f"[LAUNCHER] Bot PID {proc.pid} exited with code {rc}")
        print("[LAUNCHER] Restarting in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    main()