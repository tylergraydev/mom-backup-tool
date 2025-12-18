"""Detects external/removable drives on Windows."""

import psutil
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class DriveInfo:
    """Information about a detected drive."""
    letter: str  # e.g., "E:"
    label: str   # e.g., "My Backup Drive"
    total_gb: float
    free_gb: float

    @property
    def path(self) -> str:
        """Get the full path to the drive root."""
        return f"{self.letter}\\"

    @property
    def display_name(self) -> str:
        """Get a user-friendly display name."""
        if self.label:
            return f"{self.label} ({self.letter})"
        return f"Drive ({self.letter})"

    @property
    def unique_id(self) -> str:
        """Generate a unique identifier for this drive."""
        # Use label + total size as a simple unique ID
        return f"{self.label}_{int(self.total_gb * 1024)}"


class DriveDetector:
    """Detects and monitors external/removable drives."""

    # Drive types we consider as "external" or "removable"
    # On Windows: removable=True or fstype is common external formats
    EXTERNAL_FSTYPES = {'FAT32', 'exFAT', 'NTFS'}

    def __init__(self):
        self._last_detected: List[DriveInfo] = []

    def get_external_drives(self) -> List[DriveInfo]:
        """Get a list of all currently connected removable drives."""
        drives = []

        for partition in psutil.disk_partitions(all=False):
            # Skip system drives (usually C:)
            if partition.mountpoint == "C:\\":
                continue

            # Only include drives marked as removable (USB flash drives, SD cards)
            # The 'opts' field contains 'removable' for these drives on Windows
            if 'removable' not in partition.opts.lower():
                continue

            try:
                usage = psutil.disk_usage(partition.mountpoint)

                # Get drive label from the path
                drive_letter = partition.mountpoint.rstrip("\\")
                label = self._get_drive_label(drive_letter)

                drive_info = DriveInfo(
                    letter=drive_letter,
                    label=label,
                    total_gb=usage.total / (1024 ** 3),
                    free_gb=usage.free / (1024 ** 3)
                )
                drives.append(drive_info)

            except (PermissionError, OSError):
                # Skip drives we can't access
                continue

        self._last_detected = drives
        return drives

    def _get_drive_label(self, drive_letter: str) -> str:
        """Get the volume label for a drive."""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            volume_name_buffer = ctypes.create_unicode_buffer(1024)

            # GetVolumeInformationW to get volume label
            result = kernel32.GetVolumeInformationW(
                f"{drive_letter}\\",
                volume_name_buffer,
                ctypes.sizeof(volume_name_buffer),
                None, None, None, None, 0
            )

            if result:
                return volume_name_buffer.value
        except Exception:
            pass

        return ""

    def find_drive_with_settings(self, settings_filename: str) -> Optional[DriveInfo]:
        """Find a drive that has our settings file on it."""
        for drive in self.get_external_drives():
            settings_path = Path(drive.path) / settings_filename
            if settings_path.exists():
                return drive
        return None

    def get_first_drive(self) -> Optional[DriveInfo]:
        """Get the first available external drive, or None."""
        drives = self.get_external_drives()
        return drives[0] if drives else None
