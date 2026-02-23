# PowerShell script to set up and start the llama.cpp server (source build)
# Builds llama.cpp from source using CMake and starts the server.

# Function to check if a command exists
function Command-Exists {
    param ([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Get the script directory
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Get-Location
}

# Safety Check
if ($ScriptDir -match "system32") {
    Write-Host "Error: Script directory detected as a system folder ($ScriptDir)."
    Write-Host "Please run this script from the sandbox folder."
    Read-Host "Press Enter to exit"
    exit 1
}

$LlamaDir = Join-Path -Path $ScriptDir -ChildPath "llama.cpp"
$BuildDir = Join-Path -Path $LlamaDir   -ChildPath "build"
$ModelsDir = Join-Path -Path $LlamaDir   -ChildPath "models"
$ModelPath = Join-Path -Path $ModelsDir  -ChildPath "qwen2.5-coder-3b-instruct-q4_k_m.gguf"
$ServerPort = if ($env:LLAMA_CPP_SERVER_PORT) { $env:LLAMA_CPP_SERVER_PORT } else { "7860" }

# --------------------------------------------------------
# Step 1: Clone llama.cpp source (if not already cloned)
# --------------------------------------------------------
if (-not (Test-Path -Path (Join-Path $LlamaDir ".git"))) {
    Write-Host "Cloning llama.cpp source repository..."
    if (-not (Command-Exists git)) {
        Write-Host "Error: 'git' is not installed. Please install Git for Windows: https://git-scm.com/download/win"
        Read-Host "Press Enter to exit"
        exit 1
    }
    git clone https://github.com/ggml-org/llama.cpp.git $LlamaDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: git clone failed."
        Read-Host "Press Enter to exit"
        exit 1
    }
}
else {
    Write-Host "llama.cpp source already present, skipping clone."
}

# --------------------------------------------------------
# Step 2: Build with CMake (if not already built)
# --------------------------------------------------------
$BuiltBinary = Join-Path -Path $BuildDir -ChildPath "bin\Release\llama-server.exe"

if (-not (Test-Path -Path $BuiltBinary)) {
    Write-Host "Building llama.cpp from source (this may take several minutes)..."
    if (-not (Command-Exists cmake)) {
        Write-Host "Error: 'cmake' is not found in PATH."
        Write-Host "Please install Visual Studio Build Tools 2022 with 'Desktop development with C++' workload."
        Write-Host "Then run this script from the 'Developer Command Prompt for VS 2022'."
        Read-Host "Press Enter to exit"
        exit 1
    }

    cmake -S $LlamaDir -B $BuildDir -DLLAMA_BUILD_SERVER=ON
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: CMake configuration failed."
        Read-Host "Press Enter to exit"
        exit 1
    }

    cmake --build $BuildDir --config Release
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: CMake build failed."
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "Build complete!"
}
else {
    Write-Host "llama-server already built, skipping build."
}

# --------------------------------------------------------
# Step 3: Ensure models directory and model file exist
# --------------------------------------------------------
if (-not (Test-Path -Path $ModelsDir)) {
    New-Item -ItemType Directory -Path $ModelsDir -Force | Out-Null
}

if (-not (Test-Path -Path $ModelPath)) {
    Write-Host ""
    Write-Host "--------------------------------------------------------"
    Write-Host "Model not found at: $ModelPath"
    Write-Host "Please download the model manually:"
    Write-Host "  https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF"
    Write-Host "And place the .gguf file in: $ModelsDir"
    Write-Host "--------------------------------------------------------"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Model found at: $ModelPath"

# --------------------------------------------------------
# Step 4: Start the llama-server
# --------------------------------------------------------
Write-Host ""
Write-Host "Starting llama-server on port $ServerPort..."
Start-Process -NoNewWindow -FilePath $BuiltBinary -ArgumentList "--model", $ModelPath, "--port", $ServerPort

Write-Host ""
Write-Host "Setup complete! The llama.cpp server is starting on http://localhost:$ServerPort"
Write-Host "You can now run the sandbox app with: python sandbox_app.py"
Write-Host ""
Write-Host "Press Ctrl+C to stop."
while ($true) {
    Start-Sleep -Seconds 5
}
