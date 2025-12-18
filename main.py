"""
Mom's Backup Tool
A simple backup application for backing up files to an external drive.
"""

import sys
from backup_app import BackupApp


def main():
    test_mode = "--test" in sys.argv
    app = BackupApp(test_mode=test_mode)
    app.run()


if __name__ == "__main__":
    main()
