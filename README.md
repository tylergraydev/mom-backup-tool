# Mom's Backup Tool

A simple backup application for backing up files to an external drive.

## Download

Download the latest version from the [Releases](../../releases) page. Just download `MomBackupTool.exe` and run it.

## For Developers

### Requirements
- Python 3.10+
- psutil

### Running from source
```bash
pip install -r requirements.txt
python main.py
```

### Building the executable
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "MomBackupTool" main.py
```

The executable will be in the `dist` folder.
