"""Backup engine that copies files with progress tracking."""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, Set
from dataclasses import dataclass


@dataclass
class BackupProgress:
    """Progress information during backup."""
    total_files: int
    copied_files: int
    total_bytes: int
    copied_bytes: int
    current_file: str
    errors: list

    @property
    def percent(self) -> float:
        """Get completion percentage (0-100)."""
        if self.total_bytes == 0:
            return 0
        return (self.copied_bytes / self.total_bytes) * 100


class BackupEngine:
    """Handles the actual file backup with progress reporting."""

    # Folders to skip during backup
    EXCLUDED_FOLDERS: Set[str] = {
        # Windows temp and cache
        'Temp',
        'INetCache',
        'Cache',
        'cache',
        'cache2',
        'LocalCache',
        'CacheStorage',
        'Code Cache',
        'GPUCache',
        'ShaderCache',
        'DXCache',

        # Development
        'node_modules',
        '.git',
        '__pycache__',
        '.cache',
        'venv',
        '.venv',
        'env',
        '.env',

        # Other common junk
        'Logs',
        'logs',
        '$Recycle.Bin',
        'System Volume Information',
    }

    # Partial paths to exclude (checked with 'in')
    EXCLUDED_PATHS: Set[str] = {
        'AppData\\Local\\Temp',
        'AppData\\Local\\Microsoft\\Windows\\INetCache',
        'AppData\\Local\\Microsoft\\Windows\\Explorer',
        'AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache',
        'AppData\\Local\\Google\\Chrome\\User Data\\Default\\Code Cache',
        'AppData\\Local\\Mozilla\\Firefox\\Profiles',
        'AppData\\Local\\Packages',
        'AppData\\Local\\D3DSCache',
        'AppData\\Local\\CrashDumps',
        'AppData\\Local\\pip\\cache',
        'AppData\\Local\\npm-cache',
    }

    def __init__(self, source_dir: str, dest_drive: str):
        self.source_dir = Path(source_dir)
        self.dest_drive = Path(dest_drive)
        self._cancelled = False
        self._progress = BackupProgress(
            total_files=0,
            copied_files=0,
            total_bytes=0,
            copied_bytes=0,
            current_file="",
            errors=[]
        )

    def cancel(self):
        """Cancel the ongoing backup."""
        self._cancelled = True

    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from backup."""
        path_str = str(path)

        # Check folder name
        if path.name in self.EXCLUDED_FOLDERS:
            return True

        # Check if folder starts with $ or .
        if path.name.startswith('$'):
            return True

        # Check partial paths
        for excluded in self.EXCLUDED_PATHS:
            if excluded in path_str:
                return True

        return False

    def _count_files(self, progress_callback: Optional[Callable] = None) -> tuple:
        """Count total files and bytes to copy. Returns (file_count, byte_count)."""
        total_files = 0
        total_bytes = 0

        for root, dirs, files in os.walk(self.source_dir):
            root_path = Path(root)

            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude(root_path / d)]

            for file in files:
                if self._cancelled:
                    return total_files, total_bytes

                file_path = root_path / file
                try:
                    total_bytes += file_path.stat().st_size
                    total_files += 1
                except (OSError, PermissionError):
                    pass

        return total_files, total_bytes

    def _get_backup_folder_name(self) -> str:
        """Generate backup folder name with date and increment."""
        today = datetime.now().strftime("%Y-%m-%d")
        base_name = f"backup-{today}"

        backups_dir = self.dest_drive / "backups"
        backups_dir.mkdir(exist_ok=True)

        # Find the next available increment
        increment = 1
        while True:
            folder_name = f"{base_name}-{increment}"
            if not (backups_dir / folder_name).exists():
                return folder_name
            increment += 1

    def run(self, progress_callback: Optional[Callable[[BackupProgress], None]] = None) -> BackupProgress:
        """
        Run the backup process.

        Args:
            progress_callback: Called periodically with BackupProgress updates

        Returns:
            Final BackupProgress with results
        """
        # Count files first
        total_files, total_bytes = self._count_files()
        return self.run_with_counts(total_files, total_bytes, progress_callback)

    def run_with_counts(
        self,
        total_files: int,
        total_bytes: int,
        progress_callback: Optional[Callable[[BackupProgress], None]] = None
    ) -> BackupProgress:
        """
        Run the backup process with pre-counted file totals.

        Args:
            total_files: Pre-counted number of files
            total_bytes: Pre-counted total bytes
            progress_callback: Called periodically with BackupProgress updates

        Returns:
            Final BackupProgress with results
        """
        self._cancelled = False
        self._progress = BackupProgress(
            total_files=total_files,
            copied_files=0,
            total_bytes=total_bytes,
            copied_bytes=0,
            current_file="Starting backup...",
            errors=[]
        )

        if progress_callback:
            progress_callback(self._progress)

        if self._cancelled:
            return self._progress

        # Create backup destination
        folder_name = self._get_backup_folder_name()
        dest_dir = self.dest_drive / "backups" / folder_name

        # Copy files
        for root, dirs, files in os.walk(self.source_dir):
            if self._cancelled:
                break

            root_path = Path(root)

            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude(root_path / d)]

            for file in files:
                if self._cancelled:
                    break

                src_file = root_path / file
                rel_path = src_file.relative_to(self.source_dir)
                dest_file = dest_dir / rel_path

                self._progress.current_file = str(rel_path)

                try:
                    # Create destination directory if needed
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy the file
                    shutil.copy2(src_file, dest_file)

                    self._progress.copied_bytes += src_file.stat().st_size
                    self._progress.copied_files += 1

                except (OSError, PermissionError, shutil.Error) as e:
                    # Log error but continue
                    self._progress.errors.append(f"{rel_path}: {str(e)}")

                if progress_callback:
                    progress_callback(self._progress)

        self._progress.current_file = "Complete!"
        if progress_callback:
            progress_callback(self._progress)

        return self._progress
