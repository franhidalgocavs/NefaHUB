@echo off
REM ── Build NefaHUB  ──────────────────────────────────
REM Requires GCC (MinGW) in PATH
REM Typical MinGW path: C:\msys64\ucrt64\bin

SET PATH=C:\msys64\ucrt64\bin;%PATH%

echo [BUILD] Compiling nefahub.c ...
windres recursos.rc -o recursos.o
gcc -O2 -mwindows -o nefahub.exe nefahub.c recursos.o -lgdi32 -luser32 -lwinmm

if %ERRORLEVEL% EQU 0 (
    echo [BUILD] OK — nefahub.exe created!
    echo [BUILD] Size:
    dir /b nefahub.exe
) else (
    echo [BUILD] FAILED — check errors above.
)
pause
