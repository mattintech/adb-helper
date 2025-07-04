#!/usr/bin/env python3
"""Main CLI entry point for ADB Helper - Refactored with OoO"""

import click
from rich.console import Console
from .core.adb import ADBError
from .core.device import DeviceManager
from .commands import register_commands

console = Console()

@click.group()
@click.version_option()
@click.pass_context
def main(ctx):
    """ADB Helper - Simplify Android device management"""
    ctx.ensure_object(dict)
    try:
        ctx.obj['device_manager'] = DeviceManager()
    except ADBError as e:
        console.print(f"[red]Error: {e}[/red]")
        ctx.exit(1)

# Add helpv command
@main.command('helpv')
def helpv():
    """Show verbose help with full command tree and examples"""
    from rich.tree import Tree
    from rich.panel import Panel
    
    console.print("\n[bold]ADB Helper - Complete Command Reference[/bold]\n")
    
    # Create command tree
    tree = Tree("🤖 [bold cyan]adbh[/bold cyan]")
    
    # Basic commands
    basic = tree.add("[bold]Basic Commands[/bold]")
    basic.add("[cyan]check[/cyan] - Check system dependencies")
    basic.add("[cyan]devices[/cyan] - List connected devices")
    basic.add("[cyan]info[/cyan] - Show detailed device information\n  [dim]Example: adbh info -d device_id[/dim]")
    basic.add("[cyan]shell[/cyan] - Run shell commands\n  [dim]Example: adbh shell ls /sdcard\n  Example: adbh shell -a whoami  # Run on all devices[/dim]")
    basic.add("[cyan]enable-adb[/cyan] - Interactive guide to enable ADB debugging")
    basic.add("[cyan]disconnect[/cyan] - Disconnect wireless devices\n  [dim]Example: adbh disconnect -d 192.168.1.100:5555[/dim]")
    
    # Add device commands
    add_device = tree.add("[bold]Add Device Commands[/bold] ([cyan]adbh add-device[/cyan])")
    add_device.add("[cyan]usb[/cyan] - Add a device via USB connection")
    add_device.add("[cyan]wireless[/cyan] - Connect to a paired device via WiFi\n  [dim]Example: adbh add-device wireless 192.168.1.100:5555[/dim]")
    add_device.add("[cyan]pair[/cyan] - Pair a new device for wireless debugging\n  [dim]Example: adbh add-device pair\n  Example: adbh add-device pair --discover[/dim]")
    add_device.add("[cyan]qrcode[/cyan] - QR code pairing (experimental)\n  [dim]Example: adbh add-device qrcode --experimental[/dim]")
    
    # App commands
    app = tree.add("[bold]App Management[/bold] ([cyan]adbh app[/cyan])")
    app.add("[cyan]list[/cyan] - List installed applications\n  [dim]Example: adbh app list\n  Example: adbh app list -s  # Include system apps\n  Example: adbh app list -f chrome  # Filter by name[/dim]")
    app.add("[cyan]launch[/cyan] - Launch an application\n  [dim]Example: adbh app launch com.android.chrome\n  Example: adbh app launch  # Interactive selection[/dim]")
    app.add("[cyan]clear[/cyan] - Clear app data and cache\n  [dim]Example: adbh app clear com.example.app\n  Example: adbh app clear -c  # Cache only\n  Example: adbh app clear -y  # Skip confirmation[/dim]")
    app.add("[cyan]stop[/cyan] - Force stop an application\n  [dim]Example: adbh app stop com.example.app[/dim]")
    app.add("[cyan]info[/cyan] - Show detailed app information\n  [dim]Example: adbh app info com.android.chrome[/dim]")
    app.add("[cyan]backup[/cyan] - Backup APK file(s) from device\n  [dim]Example: adbh app backup com.example.app\n  Example: adbh app backup -a  # All apps\n  Example: adbh app backup -o ~/Desktop/apks[/dim]")
    app.add("[cyan]current[/cyan] - Show current foreground app\n  [dim]Example: adbh app current\n  Example: adbh app current -w  # Watch mode\n  Example: adbh app current -w -i 2  # 2 second interval[/dim]")
    
    # Capture commands
    capture = tree.add("[bold]Screen Capture[/bold] ([cyan]adbh capture[/cyan])")
    capture.add("[cyan]screenshot[/cyan] - Take a screenshot\n  [dim]Example: adbh capture screenshot\n  Example: adbh capture screenshot -o ~/Pictures\n  Example: adbh capture screenshot -f my_screen.png[/dim]")
    capture.add("[cyan]screenrecord[/cyan] - Record device screen\n  [dim]Example: adbh capture screenrecord\n  Example: adbh capture screenrecord -t 30  # 30 seconds\n  Example: adbh capture screenrecord -b 4M  # 4Mbps bitrate[/dim]")
    
    # Log commands
    log = tree.add("[bold]Log Management[/bold] ([cyan]adbh log[/cyan])")
    log.add("[cyan]view[/cyan] - View device logs (supports multiple devices with color coding)\n  [dim]Example: adbh log view\n  Example: adbh log view -f com.example.app  # Filter by app\n  Example: adbh log view --separate  # Multiple devices in separate windows[/dim]")
    log.add("[cyan]dump[/cyan] - Dump current logs and exit\n  [dim]Example: adbh log dump\n  Example: adbh log dump -f com.example.app -s  # Filter and save[/dim]")
    log.add("[cyan]clear[/cyan] - Clear device logs\n  [dim]Example: adbh log clear[/dim]")
    
    console.print(tree)
    
    # Common workflows panel
    workflows = Panel(
        "[bold]Common Workflows:[/bold]\n\n"
        "1. [cyan]Connect wirelessly:[/cyan]\n"
        "   adbh add-device pair       # First time pairing\n"
        "   adbh add-device wireless   # Connect after pairing\n\n"
        "2. [cyan]Debug an app:[/cyan]\n"
        "   adbh app info com.example.app\n"
        "   adbh log view -f com.example.app\n"
        "   adbh app clear com.example.app\n\n"
        "3. [cyan]Backup apps:[/cyan]\n"
        "   adbh app list              # See what's installed\n"
        "   adbh app backup -a -o ~/backup  # Backup all apps\n\n"
        "4. [cyan]Monitor app usage:[/cyan]\n"
        "   adbh app current -w        # Watch active app changes\n\n"
        "5. [cyan]Capture for documentation:[/cyan]\n"
        "   adbh capture screenshot\n"
        "   adbh capture screenrecord -t 30",
        title="[bold]💡 Tips[/bold]",
        border_style="blue"
    )
    
    console.print("\n")
    console.print(workflows)
    
    # Global options
    console.print("\n[bold]Global Options:[/bold]")
    console.print("  [cyan]-d, --device[/cyan]  Target specific device (works with most commands)")
    console.print("  [cyan]--help[/cyan]        Show help for any command")
    console.print("  [cyan]--version[/cyan]     Show version information\n")

# Register all commands with the main group
register_commands(main)

if __name__ == "__main__":
    main()