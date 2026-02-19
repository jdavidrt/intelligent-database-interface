# PowerShell script to set up the environment for running the sandbox

# Function to check if a command exists
function Command-Exists {
    param (
        [string]$Command
    )
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Get the script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) {
    $ScriptDir = Get-Location
}

# Step 1: Install llama.cpp via winget
if (-not (Command-Exists llama-server)) {
    Write-Host "Installing llama.cpp via winget..."
    if (-not (Command-Exists winget)) {
        Write-Host "Error: 'winget' is not available. Please install App Installer from the Microsoft Store."
        Read-Host "Press Enter to exit"
        exit 1
    }
    winget install llama.cpp
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to install llama.cpp. Please check the output above for details."
        Read-Host "Press Enter to exit"
        exit 1
    }
    # Refresh PATH so llama-server is available in the current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Host "llama.cpp installed successfully."
} else {
    Write-Host "llama.cpp is already installed."
}

# Step 2: Ensure models directory exists
$ModelsDir = Join-Path -Path $ScriptDir -ChildPath "llama.cpp/models"
if (-not (Test-Path -Path $ModelsDir)) {
    Write-Host "Creating models directory..."
    New-Item -ItemType Directory -Path $ModelsDir | Out-Null
}

# Step 3: Download Qwen2.5-Coder-3B-Instruct model
$ModelPath = Join-Path -Path $ModelsDir -ChildPath "qwen2.5-coder-3b-instruct-q4_k_m.gguf"
if (-not (Test-Path -Path $ModelPath)) {
    Write-Host "Downloading Qwen2.5-Coder-3B-Instruct model..."
    $HuggingFaceToken = $env:HUGGINGFACE_TOKEN
    if (-not $HuggingFaceToken) {
        Write-Host "Error: Hugging Face token not found. Please set the HUGGINGFACE_TOKEN environment variable and try again."
        Read-Host "Press Enter to exit"
        exit 1
    }
    Invoke-WebRequest -Uri "https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/qwen2.5-coder-3b-instruct-q4_k_m.gguf" -Headers @{ Authorization = "Bearer $HuggingFaceToken" } -OutFile $ModelPath
    if (-not (Test-Path -Path $ModelPath)) {
        Write-Host "Error: Failed to download the model. Please check your Hugging Face token and internet connection."
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "Model downloaded successfully."
} else {
    Write-Host "Model already exists."
}

# Step 4: Start llama.cpp server
Write-Host "Starting llama.cpp server..."
if (-not (Command-Exists llama-server)) {
    Write-Host "Error: 'llama-server' not found. Please restart your terminal and try again, or verify that llama.cpp was installed correctly."
    Read-Host "Press Enter to exit"
    exit 1
}
Start-Process -NoNewWindow -FilePath "llama-server" -ArgumentList "--model", $ModelPath, "--port", "8080"

Write-Host ""
Write-Host "Setup complete! The llama.cpp server is running on http://localhost:8080"
Write-Host "You can now run the sandbox app with: python sandbox_app.py"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server."
# Keep the script open so the server keeps running
while ($true) {
    Start-Sleep -Seconds 5
}
