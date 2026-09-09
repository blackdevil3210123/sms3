#!/usr/bin/env python3
import subprocess, time, sys, os

BOT_SCRIPT = "/app/main.py"

def main():
    print("[LAUNCHER] SMS Blast Bot Starting...")
    print("[LAUNCHER] Bot: @Blackdeviltoolowner_bot")
    
    while True:
        # Kill old processes using ps (which is available in all Linux)
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'main.py' in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            if pid != os.getpid():
                                os.kill(pid, 9)
                                print(f"[LAUNCHER] Killed PID: {pid}")
                        except:
                            pass
        except Exception as e:
            print(f"[LAUNCHER] Kill error: {e}")
        
        time.sleep(2)
        
        # Start bot
        proc = subprocess.Popen(
            [sys.executable, BOT_SCRIPT],
            cwd="/app"
        )
        print(f"[LAUNCHER] Started bot PID: {proc.pid}")
        
        rc = proc.wait()
        print(f"[LAUNCHER] Bot exited with code: {rc}")
        print("[LAUNCHER] Restarting in 3 seconds...")
        time.sleep(3)

if __name__ == "__main__":
    main()
