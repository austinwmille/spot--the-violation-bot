# spot, the bot, only works if I manually change the sound output for Spotify
# I go to advanced sound settings and leave everything on default!!
# EXCEPT for the output field for the Spotify app
# I change that to "CABLE Input (VB-Audio Virtual Cable)"
# This script is used by the bot to change Spotify output automatically, and change it back when it is stopped
# STILL A WIP; IT BROKEN AF

# Action to take: 'start' or 'stop'
param (
    [string]$action
)

# Path to NirCmd executable
$nircmd = "C:\Users\austi\extra path stuff\nircmd-x64\nircmd.exe"

# Switch Spotify to CABLE Input
if ($action -eq "start") {
    Write-Host "Switching Spotify output to CABLE Input..."
    & $nircmd setappvolume "Spotify.exe" 1
    & $nircmd setdefaultsounddevice "CABLE Input (VB-Audio Virtual Cable)" 1
}

# Switch Spotify back to Default (Speakers/Headphones)
if ($action -eq "stop") {
    Write-Host "Switching Spotify output back to default..."
    & $nircmd setdefaultsounddevice "Default" 1
}
