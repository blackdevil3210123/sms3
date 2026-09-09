#!/usr/bin/env python3
import subprocess, time, sys, os

BOT_SCRIPT = "/app/main.py"

def main():
    print("[LAUNCHER] SMS Blast Bot Starting...")
    print("[LAUNCHER] Bot: @Blackdeviltoolowner_bot")
    
    while True:
        # Kill old processes
        try:
            os.system("pkill -f 'python.*main.py' 2>/dev/null || true")
        except:
            pass
        time.sleep(2)
        
        # Start bot
        proc = subprocess.Popen(
            [sys.executable, BOT_SCRIPT],
            cwd="/app",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"[LAUNCHER] Started bot PID: {proc.pid}")
        
        # Wait for bot to exit
        rc = proc.wait()
        print(f"[LAUNCHER] Bot exited with code: {rc}")
        print("[LAUNCHER] Restarting in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    main()
