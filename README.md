Usage:

Setup:
```
cd <path_to_files>
python -m venv venv
.\venv\Scripts\activate.ps1
pip install -r requirements.txt
```

Starting (After Setup):
```
python Record.py
cd <path_to_files>
.\venv\Scripts\activate.ps1
python Record.py
```

Buttons:

Start: Starts recording

Stop: Stops Recording

Export: exports to .avi

Pause: Pauses Recording


To Make a Shortcut (Windows Desktop):
```
pip install pyinstaller
cd <path_to_files>
pyinstaller --onefile --windowed --icon=ScreenRecorderIcon.ico Record.py
```
Copy the newly made .exe path from pyinstaller in <current_dir\dist>
Right click on desktop then:

New ==> Shortcut

Add the Path to the .exe in the shortcut menu. Lastly, click 'Next' then 'Finished'
