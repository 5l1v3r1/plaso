@echo off
del /q /s dist\plaso 2> NUL

rmdir /q /s dist\plaso 2> NUL

mkdir dist\plaso
mkdir dist\plaso\licenses

xcopy /q /y ACKNOWLEDGEMENT dist\plaso
xcopy /q /y AUTHORS dist\plaso
xcopy /q /y LICENSE.TXT dist\plaso
xcopy /q /y config\licenses\* dist\plaso\licences

xcopy /q /y /s dist\image_export\* dist\plaso
xcopy /q /y /s dist\log2timeline\* dist\plaso
xcopy /q /y /s dist\pinfo\* dist\plaso
xcopy /q /y /s dist\plasm\* dist\plaso
xcopy /q /y /s dist\pprof\* dist\plaso
xcopy /q /y /s dist\preg\* dist\plaso
xcopy /q /y /s dist\pshell\* dist\plaso
xcopy /q /y /s dist\psort\* dist\plaso
