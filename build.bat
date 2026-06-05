@echo off
REM ── Build NefaHUB Premium ──────────────────────────────────
REM Requires GCC (MinGW) in PATH
REM Typical MinGW path: C:\msys64\ucrt64\bin

SET PATH=C:\msys64\ucrt64\bin;%PATH%

echo [BUILD] Compiling nefahub_premium.c ...
gcc -O2 -mwindows -o nefahub_premium.exe nefahub_premium.c -lgdi32 -luser32 -lwinmm

if %ERRORLEVEL% EQU 0 (
    echo [BUILD] OK — nefahub_premium.exe created!
    echo [BUILD] Size:
    dir /b nefahub_premium.exe
) else (
    echo [BUILD] FAILED — check errors above.
)
pause
