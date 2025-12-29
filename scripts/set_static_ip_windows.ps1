# Set Static IP Address Script for Windows
# Run this script as Administrator

# Check for Administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "You do not have Administrator rights to run this script!`nPlease re-run this script as an Administrator."
    Pause
    exit
}

Clear-Host
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   GoGospelNow - Static IP Setup Tool" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This tool will help you set a static IP address for your computer."
Write-Host "A static IP helps your congregation connect reliably to the listener app."
Write-Host ""

# Get Network Adapters
$interfaces = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }

if ($interfaces.Count -eq 0) {
    Write-Error "No active network adapters found."
    Pause
    exit
}

Write-Host "Available Network Interfaces:" -ForegroundColor Yellow
$i = 1
foreach ($iface in $interfaces) {
    Write-Host "[$i] $($iface.Name) - $($iface.InterfaceDescription)"
    $i++
}
Write-Host ""

# User Selection
$selection = Read-Host "Select interface number (e.g., 1)"
$index = [int]$selection - 1

if ($index -lt 0 -or $index -ge $interfaces.Count) {
    Write-Error "Invalid selection."
    Pause
    exit
}

$selectedInterface = $interfaces[$index]
Write-Host "Selected: $($selectedInterface.Name)" -ForegroundColor Green
Write-Host ""

# IP Configuration Input
$ipAddress = Read-Host "Enter desired Static IP address [Default: 192.168.1.100]"
if ([string]::IsNullOrWhiteSpace($ipAddress)) { $ipAddress = "192.168.1.100" }

$subnetPrefix = Read-Host "Enter Subnet Prefix Length (24 = 255.255.255.0) [Default: 24]"
if ([string]::IsNullOrWhiteSpace($subnetPrefix)) { $subnetPrefix = "24" }

# Try to detect gateway
$currentConfig = Get-NetIPConfiguration -InterfaceAlias $selectedInterface.Name
$defaultGateway = $currentConfig.IPv4DefaultGateway.NextHop
if (-not $defaultGateway) { $defaultGateway = "192.168.1.1" }

$gateway = Read-Host "Enter Gateway IP [Default: $defaultGateway]"
if ([string]::IsNullOrWhiteSpace($gateway)) { $gateway = $defaultGateway }

$dns = Read-Host "Enter DNS Server [Default: 8.8.8.8]"
if ([string]::IsNullOrWhiteSpace($dns)) { $dns = "8.8.8.8" }

Write-Host ""
Write-Host "Summary of Changes:" -ForegroundColor Yellow
Write-Host "Interface: $($selectedInterface.Name)"
Write-Host "IP Address: $ipAddress"
Write-Host "Subnet: /$subnetPrefix"
Write-Host "Gateway: $gateway"
Write-Host "DNS: $dns"
Write-Host ""

$confirm = Read-Host "Apply these settings now? (y/n)"
if ($confirm -ne 'y') {
    Write-Host "Operation cancelled."
    exit
}

# Apply Settings
try {
    Write-Host "Applying settings... (this may disconnect you briefly)" -ForegroundColor Cyan
    
    # Remove existing IP addresses to avoid conflicts (optional but recommended for clean switch)
    # Remove-NetIPAddress -InterfaceAlias $selectedInterface.Name -Confirm:$false -ErrorAction SilentlyContinue

    New-NetIPAddress -InterfaceAlias $selectedInterface.Name `
                     -IPAddress $ipAddress `
                     -PrefixLength $subnetPrefix `
                     -DefaultGateway $gateway `
                     -AddressFamily IPv4 `
                     -ErrorAction Stop

    Set-DnsClientServerAddress -InterfaceAlias $selectedInterface.Name -ServerAddresses $dns

    Write-Host ""
    Write-Host "SUCCESS! Static IP has been set." -ForegroundColor Green
    Write-Host "Current IP Configuration:"
    Get-NetIPConfiguration -InterfaceAlias $selectedInterface.Name
}
catch {
    Write-Error "Failed to set static IP: $_"
    Write-Host "Trying to set via 'Set-NetIPAddress' instead of 'New'..."
    try {
         Set-NetIPAddress -InterfaceAlias $selectedInterface.Name `
                     -IPAddress $ipAddress `
                     -PrefixLength $subnetPrefix `
                     -DefaultGateway $gateway `
                     -ErrorAction Stop
         
         Set-DnsClientServerAddress -InterfaceAlias $selectedInterface.Name -ServerAddresses $dns
         Write-Host "SUCCESS! Static IP updated." -ForegroundColor Green
    } catch {
        Write-Error "Could not update IP. Error: $_"
    }
}

Pause
