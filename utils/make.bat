@echo off
del /q /s build dist
rmdir /q /s build dist

set PYTHONPATH=C:\plaso-build\

C:\Python27\python.exe ..\pyinstaller\pyinstaller.py --onedir frontend\log2timeline.py
C:\Python27\python.exe ..\pyinstaller\pyinstaller.py --onedir frontend\plaso_information.py
C:\Python27\python.exe ..\pyinstaller\pyinstaller.py --onedir frontend\plaso_console.py
C:\Python27\python.exe ..\pyinstaller\pyinstaller.py --onedir frontend\pprof.py
C:\Python27\python.exe ..\pyinstaller\pyinstaller.py --onedir frontend\psort.py
