param(
    [string]$SourceRoot = "E:\",
    [string]$DestinationRoot = "C:\Users\kyama\OneDrive\Desktop\nfc-system-original-files\old data"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null

$items = @(
    @{ Source = Join-Path $SourceRoot "home"; Target = Join-Path $DestinationRoot "home" },
    @{ Source = Join-Path $SourceRoot "etc\mysql"; Target = Join-Path $DestinationRoot "etc_mysql" },
    @{ Source = Join-Path $SourceRoot "etc\nfc"; Target = Join-Path $DestinationRoot "etc_nfc" },
    @{ Source = Join-Path $SourceRoot "etc\systemd\system"; Target = Join-Path $DestinationRoot "etc_systemd_system" },
    @{ Source = Join-Path $SourceRoot "var\www"; Target = Join-Path $DestinationRoot "var_www" },
    @{ Source = Join-Path $SourceRoot "var\lib\mysql"; Target = Join-Path $DestinationRoot "var_lib_mysql" },
    @{ Source = Join-Path $SourceRoot "var\rootfs\home"; Target = Join-Path $DestinationRoot "nested_rootfs_home" },
    @{ Source = Join-Path $SourceRoot "var\rootfs\etc\mysql"; Target = Join-Path $DestinationRoot "nested_rootfs_etc_mysql" },
    @{ Source = Join-Path $SourceRoot "var\rootfs\etc\nfc"; Target = Join-Path $DestinationRoot "nested_rootfs_etc_nfc" },
    @{ Source = Join-Path $SourceRoot "var\rootfs\etc\systemd\system"; Target = Join-Path $DestinationRoot "nested_rootfs_etc_systemd_system" },
    @{ Source = Join-Path $SourceRoot "var\rootfs\var\www"; Target = Join-Path $DestinationRoot "nested_rootfs_var_www" },
    @{ Source = Join-Path $SourceRoot "var\rootfs\var\lib\mysql"; Target = Join-Path $DestinationRoot "nested_rootfs_var_lib_mysql" }
)

$manifest = @()
foreach ($item in $items) {
    if (Test-Path -LiteralPath $item.Source) {
        New-Item -ItemType Directory -Force -Path $item.Target | Out-Null
        robocopy $item.Source $item.Target /E /R:1 /W:1 /NFL /NDL /NP /XD ".cache" "Cache" "Code Cache" "GPUCache" "ShaderCache" "mesa_shader_cache_db" "chromium" | Out-Host
        $manifest += "COPIED: $($item.Source) -> $($item.Target)"
    } else {
        $manifest += "MISSING: $($item.Source)"
    }
}

$manifest | Set-Content -LiteralPath (Join-Path $DestinationRoot "COPY_MANIFEST.txt")
Write-Host "Old data copy complete: $DestinationRoot"