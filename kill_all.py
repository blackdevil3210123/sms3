#!/usr/bin/env python3
"""Kill ALL main.py instances aggressively."""
import subprocess, os, signal, time

def kill_all():
    out = subprocess.run(["pgrep", "-f", "main.py"], capture_output=True, text=True)
    pids = [p.strip() for p in out.stdout.split() if p.strip()]
    print(f"Found PIDs: {pids}")
    
    killed = 0
    for pid in pids:
        try:
            pid_int = int(pid)
            if pid_int == os.getpid():
                continue
            os.kill(pid_int, signal.SIGKILL)
            print(f"Killed PID {pid_int}")
            killed += 1
        except ProcessLookupError:
            print(f"PID {pid} already gone")
        except Exception as e:
            print(f"Could not kill PID {pid}: {e}")
    
    print(f"Killed {killed} processes total")
    time.sleep(3)
    
    out2 = subprocess.run(["pgrep", "-f", "main.py"], capture_output=True, text=True)
    remaining = [p.strip() for p in out2.stdout.split() if p.strip() and int(p.strip()) != os.getpid()]
    if remaining:
        print(f"WARNING: Still running: {remaining}")
        for pid in remaining:
            try:
                os.kill(int(pid), signal.SIGKILL)
                print(f"Force-killed remaining PID {pid}")
            except Exception as e:
                print(f"Could not force-kill {pid}: {e}")
        time.sleep(2)
    else:
        print("ALL CLEAR - no main.py processes running")

if __name__ == "__main__":
    kill_all()