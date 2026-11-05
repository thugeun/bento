"""Run every headless test in this folder (offscreen Qt) and report pass/fail.

    conda activate bento
    python tests/run_all.py

Each test_*.py is a standalone script that prints "... OK" and exits 0 on success.
test_wheel_real.py needs a real Windows desktop (SendInput); it is skipped when
QT_QPA_PLATFORM=offscreen is set or when not on Windows.
"""
import glob, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_HEADLESS = {"test_wheel_real.py"}

def main():
    failed = []
    for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
        name = os.path.basename(path)
        if name in SKIP_HEADLESS and (os.environ.get("QT_QPA_PLATFORM") == "offscreen" or sys.platform != "win32"):
            print(f"{name}: skipped (needs a real desktop)")
            continue
        r = subprocess.run([sys.executable, path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        status = "OK" if r.returncode == 0 else "FAIL"
        print(f"{name}: {status}  {last}")
        if r.returncode != 0:
            failed.append(name)
            print(r.stdout)
    print(f"\n{len(failed)} failed" if failed else "\nall passed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
