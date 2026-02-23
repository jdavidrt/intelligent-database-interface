@echo off
setlocal enabledelayedexpansion

set "LLAMA_DIR=llama.cpp"
set "BUILD_DIR=%LLAMA_DIR%\build"

echo IDI Sandbox Build Script
echo ========================

:: Step 0: Check for Git
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Error: 'git' is not installed or not in PATH.
    echo Please install Git for Windows: https://git-scm.com/download/win
    pause
    exit /b 1
)

:: Step 1: Clone llama.cpp if it doesn't exist
if exist "%LLAMA_DIR%" (
    if not exist "%LLAMA_DIR%\.git" (
        echo [!] Found existing '%LLAMA_DIR%' folder but it is NOT a git repository.
        echo This likely contains old pre-built binaries that need to be replaced.
        set /p "RENAME=Rename existing folder to '%LLAMA_DIR%_old' and continue? (y/n): "
        if /i "!RENAME!"=="y" (
            echo Renaming folder...
            ren "%LLAMA_DIR%" "%LLAMA_DIR%_old"
        ) else (
            echo Aborting. Please manually delete or move the '%LLAMA_DIR%' folder.
            pause
            exit /b 1
        )
    )
)

if not exist "%LLAMA_DIR%\.git" (
    echo [>] Cloning llama.cpp source...
    git clone https://github.com/ggml-org/llama.cpp.git "%LLAMA_DIR%"
    if !ERRORLEVEL! neq 0 (
        echo [!] Error: git clone failed.
        pause
        exit /b !ERRORLEVEL!
    )
) else (
    echo [OK] llama.cpp source already present.
)

:: Step 2: Check for CMake
where cmake >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Error: 'cmake' is not recognized.
    echo.
    echo Are you running this from the correct terminal?
    echo Please use the "Developer Command Prompt for VS 2022" (search in Start Menu).
    echo.
    echo If you already have it open, make sure "C++ CMake tools for Windows" 
    echo was selected during the Visual Studio Build Tools installation.
    pause
    exit /b 1
)

:: Step 3: Configure and Build
echo [>] Configuring with CMake...
cmake -S "%LLAMA_DIR%" -B "%BUILD_DIR%" -DLLAMA_BUILD_SERVER=ON
if !ERRORLEVEL! neq 0 (
    echo [!] Error: CMake configuration failed.
    pause
    exit /b !ERRORLEVEL!
)

echo [>] Building in Release mode (this may take a few minutes)...
cmake --build "%BUILD_DIR%" --config Release
if !ERRORLEVEL! neq 0 (
    echo [!] Error: CMake build failed.
    pause
    exit /b !ERRORLEVEL!
)

echo.
echo [DONE] Build complete!
echo Binary created at: %BUILD_DIR%\bin\Release\llama-server.exe
echo.
echo You can now run: python sandbox_app.py
echo.
pause
