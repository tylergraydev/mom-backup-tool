"""Settings file management for the backup tool."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

SETTINGS_FILENAME = ".mom_backup_settings.json"


class Settings:
    """Manages the settings file stored on the backup drive."""

    def __init__(self, drive_path: str):
        self.drive_path = Path(drive_path)
        self.settings_file = self.drive_path / SETTINGS_FILENAME
        self._data = {
            "drive_id": "",
            "last_backup": None,
            "backup_count": 0
        }

    def exists(self) -> bool:
        """Check if settings file exists on the drive."""
        return self.settings_file.exists()

    def load(self) -> bool:
        """Load settings from the drive. Returns True if successful."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                return True
        except (json.JSONDecodeError, IOError):
            pass
        return False

    def save(self) -> bool:
        """Save settings to the drive. Returns True if successful."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2)
            return True
        except IOError:
            return False

    def initialize(self, drive_id: str) -> bool:
        """Initialize settings for a new backup drive."""
        self._data = {
            "drive_id": drive_id,
            "last_backup": None,
            "backup_count": 0
        }
        return self.save()

    def record_backup(self) -> bool:
        """Record that a backup was completed now."""
        self._data["last_backup"] = datetime.now().isoformat()
        self._data["backup_count"] = self._data.get("backup_count", 0) + 1
        return self.save()

    def get_last_backup(self) -> Optional[datetime]:
        """Get the datetime of the last backup, or None if never backed up."""
        last = self._data.get("last_backup")
        if last:
            try:
                return datetime.fromisoformat(last)
            except ValueError:
                pass
        return None

    def was_backed_up_today(self) -> bool:
        """Check if a backup was completed today."""
        last = self.get_last_backup()
        if last:
            return last.date() == datetime.now().date()
        return False

    def get_backup_count(self) -> int:
        """Get the total number of backups made to this drive."""
        return self._data.get("backup_count", 0)

    def get_drive_id(self) -> str:
        """Get the drive identifier."""
        return self._data.get("drive_id", "")
