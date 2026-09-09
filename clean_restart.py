#!/usr/bin/env python3
"""Clean restart: kill ALL bot processes, then start exactly ONE instance."""
import subprocess, time, os, signal, sys

def kill_all_bots():
    out = subprocess.run(["pgrep", "-f", "python.*main.py"], capture_output=True, text=True)
    pids = [p for p in out.stdout.split() if p.strip()]
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGKILL)
            print(f"Killed bot PID {pid}")
        except Exception as e:
            print(f"Could not kill {pid}: {e}")
    time.sleep(4)
    out2 = subprocess.run(["pgrep", "-f", "python.*main.py"], capture_output=True, text=True)
    remaining = [p for p in out2.stdout.split() if p.strip()]
    print(f"Remaining bot processes after kill: {len(remaining)}")
    return len(remaining) == 0

def start_bot():
    open("/app/bot.log", "w").close()
    proc = subprocess.Popen(
        [sys.executable, "/app/main.py"],
        stdout=open("/app/bot.log", "a"),
        stderr=subprocess.STDOUT,
        cwd="/app",
        start_new_session=True,
    )
    print(f"Started ONE bot instance, PID: {proc.pid}")
    return proc.pid

if __name__ == "__main__":
    ok = kill_all_bots()
    pid = start_bot()
    time.sleep(15)
    out = subprocess.run(["pgrep", "-f", "python.*main.py"], capture_output=True, text=True)
    alive = [p for p in out.stdout.split() if p.strip()]
    print(f"Bot processes alive after 15s: {len(alive)} -> {alive}")
    with open("/app/bot.log") as f:
        lines = f.readlines()
    print("=== LAST 15 LOG LINES ===")
    print("".join(lines[-15:]))