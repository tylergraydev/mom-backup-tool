"""Main Tkinter application for the backup tool."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from drive_detector import DriveDetector, DriveInfo
from settings import Settings, SETTINGS_FILENAME
from backup_engine import BackupEngine, BackupProgress


class BackupApp:
    """Main backup application with Tkinter UI."""

    # UI States
    STATE_NO_DRIVE = "no_drive"
    STATE_CONFIRM_DRIVE = "confirm_drive"
    STATE_READY = "ready"
    STATE_PREPARING = "preparing"
    STATE_BACKING_UP = "backing_up"

    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode

        self.root = tk.Tk()
        title = "Mom's Backup Tool"
        if test_mode:
            title += " [TEST MODE]"
        self.root.title(title)
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Center the window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 500) // 2
        y = (self.root.winfo_screenheight() - 400) // 2
        self.root.geometry(f"500x400+{x}+{y}")

        # State
        self.detector = DriveDetector()
        self.current_drive: Optional[DriveInfo] = None
        self.settings: Optional[Settings] = None
        self.backup_engine: Optional[BackupEngine] = None
        self.state = self.STATE_NO_DRIVE
        self._test_settings_data = {}  # In-memory settings for test mode

        # Configure styles
        self._configure_styles()

        # Create main container
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Start in "no drive" state
        self._show_no_drive()

        # Start polling for drives (or simulate in test mode)
        if test_mode:
            # In test mode, show "no drive" for 2 seconds, then simulate detection
            self.root.after(2000, self._test_simulate_drive_detected)
        else:
            self._poll_for_drives()

    def _configure_styles(self):
        """Configure ttk styles for the app."""
        style = ttk.Style()

        # Large title style
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))

        # Subtitle style
        style.configure("Subtitle.TLabel", font=("Segoe UI", 12))

        # Status style
        style.configure("Status.TLabel", font=("Segoe UI", 11))

        # Success style
        style.configure("Success.TLabel", font=("Segoe UI", 12, "bold"), foreground="green")

        # Warning style
        style.configure("Warning.TLabel", font=("Segoe UI", 11), foreground="orange")

        # Big button style
        style.configure("Big.TButton", font=("Segoe UI", 14), padding=15)

        # Test mode indicator
        if self.test_mode:
            style.configure("Test.TLabel", font=("Segoe UI", 9), foreground="purple")

    def _clear_main_frame(self):
        """Remove all widgets from the main frame."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def _add_test_mode_indicator(self, container):
        """Add a test mode indicator to the UI."""
        if self.test_mode:
            test_label = ttk.Label(
                container,
                text="TEST MODE - No files will be copied",
                style="Test.TLabel"
            )
            test_label.pack(pady=(20, 0))

    def _show_no_drive(self):
        """Show the 'please plug in drive' screen."""
        self.state = self.STATE_NO_DRIVE
        self._clear_main_frame()

        # Center content
        container = ttk.Frame(self.main_frame)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Icon/emoji representation
        icon_label = ttk.Label(container, text="💾", font=("Segoe UI Emoji", 48))
        icon_label.pack(pady=(0, 20))

        # Title
        title = ttk.Label(
            container,
            text="Please plug in your backup drive",
            style="Title.TLabel"
        )
        title.pack()

        # Subtitle
        subtitle = ttk.Label(
            container,
            text="Waiting for an external drive to be connected...",
            style="Subtitle.TLabel"
        )
        subtitle.pack(pady=(10, 0))

        self._add_test_mode_indicator(container)

    def _show_confirm_drive(self, drive: DriveInfo):
        """Show the drive confirmation screen."""
        self.state = self.STATE_CONFIRM_DRIVE
        self.current_drive = drive
        self._clear_main_frame()

        # Center content
        container = ttk.Frame(self.main_frame)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Icon
        icon_label = ttk.Label(container, text="💿", font=("Segoe UI Emoji", 48))
        icon_label.pack(pady=(0, 20))

        # Title
        title = ttk.Label(
            container,
            text="External drive detected!",
            style="Title.TLabel"
        )
        title.pack()

        # Drive info
        drive_info = ttk.Label(
            container,
            text=f"{drive.display_name}\n{drive.free_gb:.1f} GB free of {drive.total_gb:.1f} GB",
            style="Subtitle.TLabel",
            justify=tk.CENTER
        )
        drive_info.pack(pady=(15, 20))

        # Question
        question = ttk.Label(
            container,
            text="Is this the drive you want to use for backups?",
            style="Status.TLabel"
        )
        question.pack(pady=(0, 20))

        # Buttons
        button_frame = ttk.Frame(container)
        button_frame.pack()

        yes_btn = ttk.Button(
            button_frame,
            text="Yes, use this drive",
            style="Big.TButton",
            command=self._on_confirm_drive
        )
        yes_btn.pack(side=tk.LEFT, padx=5)

        no_btn = ttk.Button(
            button_frame,
            text="No, wait",
            command=self._on_reject_drive
        )
        no_btn.pack(side=tk.LEFT, padx=5)

        self._add_test_mode_indicator(container)

    def _show_ready(self):
        """Show the main backup screen."""
        self.state = self.STATE_READY
        self._clear_main_frame()

        # Center content
        container = ttk.Frame(self.main_frame)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Status icon and message
        backed_up_today = False
        last_backup = None

        if self.test_mode:
            backed_up_today = self._test_settings_data.get("backed_up_today", False)
            last_backup = self._test_settings_data.get("last_backup")
        elif self.settings:
            backed_up_today = self.settings.was_backed_up_today()
            last_backup = self.settings.get_last_backup()

        if backed_up_today:
            icon_label = ttk.Label(container, text="✅", font=("Segoe UI Emoji", 48))
            icon_label.pack(pady=(0, 20))

            status = ttk.Label(
                container,
                text="Backed up successfully today!",
                style="Success.TLabel"
            )
            status.pack()
        else:
            icon_label = ttk.Label(container, text="📁", font=("Segoe UI Emoji", 48))
            icon_label.pack(pady=(0, 20))

            if last_backup:
                days_ago = (datetime.now() - last_backup).days
                if days_ago == 1:
                    status_text = "Last backup: Yesterday"
                elif days_ago < 7:
                    status_text = f"Last backup: {days_ago} days ago"
                else:
                    status_text = f"Last backup: {last_backup.strftime('%B %d, %Y')}"

                status = ttk.Label(
                    container,
                    text=status_text,
                    style="Warning.TLabel"
                )
            else:
                status = ttk.Label(
                    container,
                    text="No backups yet",
                    style="Status.TLabel"
                )
            status.pack()

        # Drive info
        if self.current_drive:
            drive_info = ttk.Label(
                container,
                text=f"Drive: {self.current_drive.display_name} ({self.current_drive.free_gb:.1f} GB free)",
                style="Subtitle.TLabel"
            )
            drive_info.pack(pady=(15, 25))

        # Backup button
        backup_btn = ttk.Button(
            container,
            text="Back Up Now",
            style="Big.TButton",
            command=self._on_backup_click
        )
        backup_btn.pack()

        self._add_test_mode_indicator(container)

    def _show_preparing(self):
        """Show the preparing/counting files screen."""
        self.state = self.STATE_PREPARING
        self._clear_main_frame()

        # Center content
        container = ttk.Frame(self.main_frame)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Icon
        icon_label = ttk.Label(container, text="🔍", font=("Segoe UI Emoji", 48))
        icon_label.pack(pady=(0, 20))

        # Title
        title = ttk.Label(
            container,
            text="Preparing backup...",
            style="Title.TLabel"
        )
        title.pack()

        # Indeterminate progress bar
        self.prep_progress_bar = ttk.Progressbar(
            container,
            length=350,
            mode='indeterminate'
        )
        self.prep_progress_bar.pack(pady=(20, 10))
        self.prep_progress_bar.start(10)

        # Status text
        self.prep_status_label = ttk.Label(
            container,
            text="Calculating backup size...",
            style="Status.TLabel"
        )
        self.prep_status_label.pack()

        self._add_test_mode_indicator(container)

    def _show_backing_up(self):
        """Show the backup progress screen."""
        self.state = self.STATE_BACKING_UP
        self._clear_main_frame()

        # Center content
        container = ttk.Frame(self.main_frame)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Icon
        icon_label = ttk.Label(container, text="⏳", font=("Segoe UI Emoji", 48))
        icon_label.pack(pady=(0, 20))

        # Title
        title = ttk.Label(
            container,
            text="Backing up your files...",
            style="Title.TLabel"
        )
        title.pack()

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            container,
            length=350,
            mode='determinate'
        )
        self.progress_bar.pack(pady=(20, 10))

        # Progress text
        self.progress_label = ttk.Label(
            container,
            text="Counting files...",
            style="Status.TLabel"
        )
        self.progress_label.pack()

        # Current file
        self.current_file_label = ttk.Label(
            container,
            text="",
            style="Subtitle.TLabel",
            wraplength=400
        )
        self.current_file_label.pack(pady=(10, 0))

        self._add_test_mode_indicator(container)

    def _poll_for_drives(self):
        """Poll for external drives every 2 seconds."""
        if self.state == self.STATE_NO_DRIVE:
            # Look for a drive with our settings file first
            drive = self.detector.find_drive_with_settings(SETTINGS_FILENAME)

            if drive:
                # Found our backup drive
                self.current_drive = drive
                self.settings = Settings(drive.path)
                self.settings.load()
                self._show_ready()
            else:
                # Check for any external drive
                drive = self.detector.get_first_drive()
                if drive:
                    self._show_confirm_drive(drive)

        elif self.state == self.STATE_READY:
            # Check if drive is still connected
            drives = self.detector.get_external_drives()
            if self.current_drive:
                still_connected = any(
                    d.letter == self.current_drive.letter
                    for d in drives
                )
                if not still_connected:
                    self.current_drive = None
                    self.settings = None
                    self._show_no_drive()

        # Schedule next poll
        self.root.after(2000, self._poll_for_drives)

    def _test_simulate_drive_detected(self):
        """Simulate a drive being detected in test mode."""
        fake_drive = DriveInfo(
            letter="E:",
            label="Mom's Backup SSD",
            total_gb=500.0,
            free_gb=342.7
        )
        self._show_confirm_drive(fake_drive)

    def _on_confirm_drive(self):
        """Handle confirming the selected drive."""
        if self.current_drive:
            if self.test_mode:
                # In test mode, just remember the drive
                self._test_settings_data = {
                    "backed_up_today": False,
                    "last_backup": None
                }
            else:
                self.settings = Settings(self.current_drive.path)
                self.settings.initialize(self.current_drive.unique_id)
            self._show_ready()

    def _on_reject_drive(self):
        """Handle rejecting the selected drive."""
        self.current_drive = None
        self._show_no_drive()

        if self.test_mode:
            # In test mode, re-detect after 2 seconds
            self.root.after(2000, self._test_simulate_drive_detected)

    def _on_backup_click(self):
        """Start the backup process."""
        if not self.current_drive:
            messagebox.showerror("Error", "No backup drive connected!")
            return

        self._show_preparing()

        # Run preparation in background thread
        if self.test_mode:
            thread = threading.Thread(target=self._run_test_backup, daemon=True)
        else:
            thread = threading.Thread(target=self._prepare_backup, daemon=True)
        thread.start()

    def _prepare_backup(self):
        """Prepare backup by counting files and checking disk space."""
        # Hardcoded to backup grayt user
        home_dir = Path("C:/Users/grayt")
        
        # Define folders to backup (common user folders)
        folders_to_backup = [
            "Documents",
            "Pictures", 
            "Videos",
            "Music",
            "Downloads",
            "Desktop"  # Common folder most users want backed up
        ]
        
        self.backup_engine = BackupEngine(str(home_dir), self.current_drive.path, folders_to_backup)

        # Count files
        total_files, total_bytes = self.backup_engine._count_files()

        # Check if drive has enough space (with 100MB buffer)
        required_bytes = total_bytes + (100 * 1024 * 1024)
        available_bytes = self.current_drive.free_gb * (1024 ** 3)

        if required_bytes > available_bytes:
            # Not enough space
            required_gb = total_bytes / (1024 ** 3)
            self.root.after(0, lambda: self._show_space_error(required_gb))
            return

        # Proceed with backup
        self.root.after(0, lambda: self._start_actual_backup(total_files, total_bytes))

    def _show_space_error(self, required_gb: float):
        """Show error when drive doesn't have enough space."""
        messagebox.showerror(
            "Not Enough Space",
            f"Your backup needs {required_gb:.1f} GB but the drive only has "
            f"{self.current_drive.free_gb:.1f} GB free.\n\n"
            "Please free up space on the backup drive or use a larger drive."
        )
        self._show_ready()

    def _start_actual_backup(self, total_files: int, total_bytes: int):
        """Start the actual backup after preparation is complete."""
        self._show_backing_up()

        # Store the counts so _run_backup can use them
        self._prepared_total_files = total_files
        self._prepared_total_bytes = total_bytes

        thread = threading.Thread(target=self._run_backup, daemon=True)
        thread.start()

    def _run_backup(self):
        """Run the backup process (called in background thread)."""
        def progress_callback(progress: BackupProgress):
            # Update UI from main thread
            self.root.after(0, lambda: self._update_progress(progress))

        # Use pre-counted values from preparation phase
        result = self.backup_engine.run_with_counts(
            self._prepared_total_files,
            self._prepared_total_bytes,
            progress_callback
        )

        # Backup complete
        self.root.after(0, lambda: self._on_backup_complete(result))

    def _run_test_backup(self):
        """Run a simulated backup in test mode."""
        # Simulate file names for realistic progress display
        test_files = [
            "Documents\\report.docx",
            "Documents\\budget.xlsx",
            "Pictures\\vacation\\IMG_001.jpg",
            "Pictures\\vacation\\IMG_002.jpg",
            "Pictures\\family\\photo1.png",
            "Desktop\\notes.txt",
            "Videos\\birthday.mp4",
            "Documents\\recipes\\cookies.pdf",
            "Pictures\\screenshots\\screen1.png",
            "Documents\\taxes\\2024.pdf",
        ]

        total_files = 1247  # Simulated total
        total_bytes = 15_800_000_000  # ~15.8 GB simulated

        # Simulate counting phase
        progress = BackupProgress(
            total_files=0,
            copied_files=0,
            total_bytes=0,
            copied_bytes=0,
            current_file="Counting files...",
            errors=[]
        )
        self.root.after(0, lambda: self._update_progress(progress))
        time.sleep(1)

        # Update with totals
        progress.total_files = total_files
        progress.total_bytes = total_bytes
        self.root.after(0, lambda p=progress: self._update_progress(p))
        time.sleep(0.5)

        # Simulate copying with progress
        for i in range(100):
            progress.copied_files = int((i / 100) * total_files)
            progress.copied_bytes = int((i / 100) * total_bytes)
            progress.current_file = test_files[i % len(test_files)]

            self.root.after(0, lambda p=BackupProgress(
                total_files=progress.total_files,
                copied_files=progress.copied_files,
                total_bytes=progress.total_bytes,
                copied_bytes=progress.copied_bytes,
                current_file=progress.current_file,
                errors=[]
            ): self._update_progress(p))

            time.sleep(0.05)  # 5 seconds total for simulation

        # Complete
        progress.copied_files = total_files
        progress.copied_bytes = total_bytes
        progress.current_file = "Complete!"

        final_progress = BackupProgress(
            total_files=total_files,
            copied_files=total_files,
            total_bytes=total_bytes,
            copied_bytes=total_bytes,
            current_file="Complete!",
            errors=[]
        )
        self.root.after(0, lambda: self._on_backup_complete(final_progress))

    def _update_progress(self, progress: BackupProgress):
        """Update the progress UI."""
        if self.state != self.STATE_BACKING_UP:
            return

        self.progress_bar['value'] = progress.percent

        if progress.total_files > 0:
            self.progress_label.config(
                text=f"{progress.copied_files:,} of {progress.total_files:,} files ({progress.percent:.0f}%)"
            )
        else:
            self.progress_label.config(text="Counting files...")

        # Truncate current file name if too long
        current = progress.current_file
        if len(current) > 50:
            current = "..." + current[-47:]
        self.current_file_label.config(text=current)

    def _on_backup_complete(self, progress: BackupProgress):
        """Handle backup completion."""
        if self.test_mode:
            # In test mode, mark as backed up today
            self._test_settings_data["backed_up_today"] = True
            self._test_settings_data["last_backup"] = datetime.now()
        elif self.settings:
            self.settings.record_backup()

        # Show completion message if there were errors
        if progress.errors:
            error_count = len(progress.errors)
            messagebox.showwarning(
                "Backup Complete",
                f"Backup finished with {error_count} file(s) that couldn't be copied.\n"
                "These are usually system files that are in use."
            )

        # Return to ready state
        self._show_ready()

    def run(self):
        """Start the application."""
        self.root.mainloop()
