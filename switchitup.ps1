$AppName = "Spotify.exe"
$NewOutputDevice = "CABLE Input (VB-Audio Virtual Cable)"

# Get the current audio session details
$audioSessions = Get-AppxPackage -AllUsers * | ForEach-Object {
    Get-Process -Name $_.Name -ErrorAction SilentlyContinue
} | Where-Object { $_.ProcessName -eq "Spotify" }

if ($audioSessions) {
    Write-Host "Found Spotify process. Attempting to change audio output..."
    $device = Get-AudioDevice -List | Where-Object { $_.Name -eq $NewOutputDevice }
    
    if ($device) {
        Set-AppVolume -ProcessName $AppName -OutputDevice $device
        Write-Host "Spotify output changed to '$NewOutputDevice'."
    } else {
        Write-Host "ERROR: Could not find '$NewOutputDevice'. Check your audio settings."
    }
} else {
    Write-Host "ERROR: Spotify is not running. Please start Spotify first."
}

if ($args[0] -eq "stop") {
    Set-AppVolume -ProcessName "Spotify.exe" -OutputDevice "Default"
    Write-Host "Spotify output reset to default."
}