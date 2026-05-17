# Docker Test Script
$ErrorActionPreference = "Continue"
Write-Host "Starting Docker test..."

try {
    $result = docker ps 2>&1
    Write-Host "Docker PS result: $result"
} catch {
    Write-Host "Error: $_"
}

Write-Host "Done."
