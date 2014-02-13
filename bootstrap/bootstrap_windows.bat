
:: This file will setup a Windows environment for use with PyExpLabSys

@ECHO OFF
if [%1]==[] GOTO usage
GOTO :check_Permissions
:parse
if "%1"=="part1" GOTO path
if "%1"=="path" GOTO path
if "%1"=="git" GOTO git
GOTO :eof

:usage
@ECHO.
@ECHO Welcome to the bootstrap PyExpLabSys for windows script
@ECHO.
@ECHO NOTE: See the file README.bootstrap_windows for requirements for this
@ECHO script.
@ECHO.
@ECHO     Usage: bootstrap_windows.bat [SECTION]
@ECHO.
@ECHO Where SECTION indicates which part of the bootstrap script that should be
@ECHO run. Possible value are listed below:
@ECHO.
@ECHO Section:
@ECHO path     Setup the PYTHONPATH to include PyExpLabSys
@ECHO git      Add common git aliasses and make it use color
@ECHO.
@ECHO part1    Both 'path' and 'git'
GOTO :eof

:check_Permissions
ECHO.
ECHO Administrative permissions required. Detecting permissions...

net session >nul 2>&1
if %errorLevel% == 0 (
    ECHO Success: Administrative permissions confirmed.
    GOTO :parse
) else (
    ECHO Failure: Current permissions inadequate.
    ECHO To open a command prompt as admin, search for cmd in Windows menu,
    ECHO press ctrl-shift-enter and confirm
    GOTO :eof
)


:path
@ECHO.
@ECHO Add C:\git\PyExpLabSys to Python path by adding a new key subkey to:
@ECHO HKEY_LOCAL_MACHINE\SOFTWARE\Python\PythonCore\2.7\PythonPath
regedit /S PyExpLabSys.reg
@ECHO ...Done
if "%1"=="part1" GOTO git
GOTO :eof

:git
@ECHO.
@ECHO Setting up git with aliasses and color
@ECHO Alias: ci "commit -v"
"c:\Program Files\Git\bin\git.exe" config --global alias.ci "commit -v"
@ECHO Alias: lol "log --graph --decorate --pretty=oneline --abbrev-commit"
"c:\Program Files\Git\bin\git.exe" config --global alias.lol "log --graph --decorate --pretty=oneline --abbrev-commit"
@ECHO Alias: ba "branch --all"
"c:\Program Files\Git\bin\git.exe" config --global alias.ba "branch --all"
@ECHO Alias: st "status"
"c:\Program Files\Git\bin\git.exe" config --global alias.st "status"
@ECHO Alias: cm "commit -m"
"c:\Program Files\Git\bin\git.exe" config --global alias.cm "commit -m"
@ECHO Color
"c:\Program Files\Git\bin\git.exe" config --global color.ui true
@ECHO ...DONE
GOTO :eof
