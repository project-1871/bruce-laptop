#!/usr/bin/env python3
import os
import sys


def main():
    if os.geteuid() != 0 and "--tui" not in sys.argv:
        print("Bruce: some tools require root (WiFi monitor mode, raw sockets).")
        print("For full functionality run: sudo python3 main.py")

    if "--tui" in sys.argv:
        from bruce.app import BruceApp
        BruceApp().run()
    else:
        from bruce.gui.app import run
        sys.exit(run())


if __name__ == "__main__":
    main()
