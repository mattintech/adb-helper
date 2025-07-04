#!/usr/bin/env python3
"""Main CLI entry point for ADB Helper"""

import click
import subprocess
from rich.console import Console
from rich.table import Table
from .core.adb import ADBWrapper, ADBError
from .core.device import DeviceManager
from .core.pairing import WiFiPairing
from .core.mdns_discovery import MDNSDiscovery

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

@main.command()
def check():
    """Check system dependencies"""
    console.print("[yellow]Checking dependencies...[/yellow]")
    
    checks = []
    
    # Check ADB
    try:
        adb = ADBWrapper()
        if adb.is_available():
            checks.append(("[green]✓[/green] ADB", "Found at " + adb.adb_path))
        else:
            checks.append(("[red]✗[/red] ADB", "Not working properly"))
    except ADBError as e:
        checks.append(("[red]✗[/red] ADB", str(e)))
    
    # Display results
    for status, message in checks:
        console.print(f"{status} {message}")
    
    if all("[green]" in check[0] for check in checks):
        console.print("\n[green]All dependencies satisfied![/green]")
    else:
        console.print("\n[red]Some dependencies are missing![/red]")

@main.command()
@click.pass_context
def devices(ctx):
    """List connected devices"""
    device_manager = ctx.obj['device_manager']
    
    try:
        devices = device_manager.list_devices()
        
        if not devices:
            console.print("[yellow]No devices found[/yellow]")
            console.print("\nMake sure:")
            console.print("  • USB debugging is enabled")
            console.print("  • Device is connected via USB")
            console.print("  • You've authorized this computer on the device")
            return
        
        table = Table(title="Connected Devices")
        table.add_column("Device ID", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Model", style="cyan")
        table.add_column("Transport", style="magenta")
        
        for device in devices:
            table.add_row(
                device["id"],
                device["status"],
                device.get("model", "Unknown"),
                device.get("transport_type", "N/A")
            )
        
        console.print(table)
        
    except ADBError as e:
        console.print(f"[red]Error: {e}[/red]")

@main.command()
@click.option('-d', '--device', help='Target device ID')
@click.pass_context
def info(ctx, device):
    """Show detailed device information"""
    device_manager = ctx.obj['device_manager']
    
    try:
        device_id = device_manager.select_device(device)
        if not device_id:
            return
        
        info = device_manager.get_device_info(device_id)
        
        console.print(f"\n[bold]Device Information[/bold]")
        console.print(f"ID: [green]{info['id']}[/green]")
        console.print(f"Manufacturer: [cyan]{info['manufacturer']}[/cyan]")
        console.print(f"Model: [cyan]{info['model']}[/cyan]")
        console.print(f"Android Version: [yellow]{info['android_version']}[/yellow]")
        console.print(f"SDK Version: [yellow]{info['sdk_version']}[/yellow]")
        console.print(f"Build Type: [magenta]{info['build_type']}[/magenta]")
        
    except ADBError as e:
        console.print(f"[red]Error: {e}[/red]")

@main.command()
def enable_adb():
    """Interactive guide to enable ADB debugging"""
    import subprocess
    import sys
    import os
    
    # Get the path to the enable_adb_helper script
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'enable_adb_helper.py')
    
    # Run the script with the current Python interpreter
    subprocess.run([sys.executable, script_path])

@main.group(name='add-device', invoke_without_command=True)
@click.pass_context
def add_device(ctx):
    """Add devices via USB or wireless connection"""
    if ctx.invoked_subcommand is None:
        # Show available options when no subcommand is provided
        console.print("\n[bold]Add Device Options:[/bold]\n")
        console.print("  [cyan]adbh add-device usb[/cyan]      - Add a device via USB")
        console.print("  [cyan]adbh add-device wireless[/cyan] - Connect to a paired device via WiFi")
        console.print("  [cyan]adbh add-device pair[/cyan]     - Pair a new device for wireless debugging")
        console.print("  [cyan]adbh add-device qrcode[/cyan]   - QR code pairing (experimental)\n")
        console.print("Use [cyan]adbh add-device --help[/cyan] for more information")

@add_device.command('usb')
@click.pass_context
def add_usb(ctx):
    """Add a device via USB connection"""
    device_manager = ctx.obj['device_manager']
    
    # Show current devices
    current_devices = device_manager.list_devices()
    if current_devices:
        console.print("\n[bold]Currently connected devices:[/bold]")
        for device in current_devices:
            console.print(f"  • {device['id']} ({device.get('model', 'Unknown')})")
    
    from .scripts.enable_adb_helper import guide_usb_debugging
    from rich.prompt import Prompt
    
    console.print("\n[yellow]Make sure the new device is connected via USB and has USB debugging enabled[/yellow]")
    input("Press Enter when ready...")
    
    # Check for new devices
    new_devices = device_manager.list_devices()
    new_count = len(new_devices) - len(current_devices)
    
    if new_count > 0:
        console.print(f"\n[green]✓ Successfully added {new_count} new device(s)![/green]")
        for device in new_devices:
            if not any(d['id'] == device['id'] for d in current_devices):
                console.print(f"  • {device['id']} ({device.get('model', 'Unknown')})")
    else:
        console.print("\n[yellow]No new devices detected.[/yellow]")
        console.print("Would you like help enabling USB debugging?")
        if Prompt.ask("Enable USB debugging guide?", choices=["y", "n"], default="y") == "y":
            guide_usb_debugging()

@add_device.command('wireless')
@click.argument('address', required=False)
@click.pass_context
def add_wireless(ctx, address):
    """Connect to a device via wireless (already paired)"""
    device_manager = ctx.obj['device_manager']
    
    try:
        if not address:
            from rich.prompt import Prompt
            console.print("\n[bold]Connect to WiFi Device[/bold]\n")
            address = Prompt.ask("Enter device address (IP:port or just IP)")
        
        # Add default port if not specified
        if ':' not in address:
            address = f"{address}:5555"
        
        console.print(f"\n[yellow]Connecting to {address}...[/yellow]")
        
        stdout, stderr, code = device_manager.adb._run_command(["connect", address])
        
        if code == 0 and "connected" in stdout.lower():
            console.print(f"[green]✓ Successfully connected to {address}![/green]")
            console.print("\nRun [cyan]adbh devices[/cyan] to see connected devices")
        else:
            console.print(f"[red]✗ Failed to connect: {stderr or stdout}[/red]")
            console.print("\nTroubleshooting:")
            console.print("• Make sure the device has wireless debugging enabled")
            console.print("• Verify both devices are on the same network")
            console.print("• Check if you need to pair first: [cyan]adbh add-device pair[/cyan]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@main.group(name='capture', invoke_without_command=True)
@click.pass_context
def capture(ctx):
    """Capture screenshots and recordings from device"""
    if ctx.invoked_subcommand is None:
        # Show available options when no subcommand is provided
        console.print("\n[bold]Capture Options:[/bold]\n")
        console.print("  [cyan]adbh capture screenshot[/cyan] - Take a screenshot")
        console.print("  [cyan]adbh capture record[/cyan]    - Record screen (video)\n")
        console.print("Use [cyan]adbh capture --help[/cyan] for more information")

@capture.command('screenshot')
@click.option('-o', '--open', 'open_file', is_flag=True, help='Open screenshot after capture')
@click.option('-d', '--device', help='Target device ID')
@click.pass_context
def screenshot(ctx, open_file, device):
    """Take a screenshot from the device"""
    device_manager = ctx.obj['device_manager']
    
    try:
        device_id = device_manager.select_device(device)
        if not device_id:
            return
        
        # Wake up the device
        console.print("[yellow]Waking up device...[/yellow]")
        device_manager.adb._run_command(["-s", device_id, "shell", "input", "keyevent", "KEYCODE_WAKEUP"])
        
        # Small delay to ensure screen is on
        import time
        time.sleep(0.5)
        
        import os
        from datetime import datetime
        
        # Create screenshots directory
        screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Get current time
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        
        # Count existing screenshots for this minute
        existing_files = [f for f in os.listdir(screenshots_dir) if f.startswith(time_str)]
        screenshot_num = len(existing_files) + 1
        
        # Try to get foreground app name
        app_name = ""
        try:
            stdout, _, _ = device_manager.adb._run_command([
                "-s", device_id, "shell", 
                "dumpsys", "window", "windows", "|", "grep", "-E", "'mCurrentFocus|mFocusedApp'"
            ])
            
            # Extract app name from output
            import re
            match = re.search(r'[^/]+/([^}\s]+)', stdout)
            if match:
                app_name = f"-{match.group(1).split('.')[-1]}"
        except:
            pass
        
        # Create filename
        filename = f"{time_str}-{screenshot_num}{app_name}.png"
        filepath = os.path.join(screenshots_dir, filename)
        
        # Take screenshot directly to file
        console.print(f"[yellow]Taking screenshot...[/yellow]")
        process = subprocess.run([
            device_manager.adb.adb_path, "-s", device_id, "exec-out", "screencap", "-p"
        ], capture_output=True)
        
        if process.returncode == 0:
            with open(filepath, 'wb') as f:
                f.write(process.stdout)
            console.print(f"[green]✓ Screenshot saved to: {filepath}[/green]")
            
            # Open the file if requested
            if open_file:
                import platform
                import webbrowser
                
                # Use webbrowser which handles cross-platform opening
                webbrowser.open(f'file://{os.path.abspath(filepath)}')
                console.print(f"[green]✓ Opening screenshot...[/green]")
        else:
            console.print(f"[red]Failed to capture screenshot: {process.stderr.decode()}[/red]")
                
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@capture.command('record')
@click.option('-t', '--time', default=180, help='Recording duration in seconds (default: 180)')
@click.option('-d', '--device', help='Target device ID')
@click.pass_context
def record(ctx, time, device):
    """Record screen video from the device"""
    device_manager = ctx.obj['device_manager']
    
    try:
        device_id = device_manager.select_device(device)
        if not device_id:
            return
        
        # Wake up the device
        console.print("[yellow]Waking up device...[/yellow]")
        device_manager.adb._run_command(["-s", device_id, "shell", "input", "keyevent", "KEYCODE_WAKEUP"])
        
        import os
        from datetime import datetime
        
        # Create recordings directory
        recordings_dir = os.path.join(os.getcwd(), "recordings")
        os.makedirs(recordings_dir, exist_ok=True)
        
        # Create filename with timestamp
        now = datetime.now()
        filename = now.strftime("recording_%Y%m%d_%H%M%S.mp4")
        filepath = os.path.join(recordings_dir, filename)
        
        # Temporary file on device
        temp_file = f"/sdcard/{filename}"
        
        console.print(f"[yellow]Recording for {time} seconds...[/yellow]")
        console.print("[dim]Press Ctrl+C to stop early[/dim]")
        
        try:
            # Start recording
            process = device_manager.adb._run_command_async([
                "-s", device_id, "shell", "screenrecord", 
                "--time-limit", str(time), temp_file
            ])
            
            # Wait for recording to complete or user interrupt
            process.wait()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping recording...[/yellow]")
            # Kill the screenrecord process
            device_manager.adb._run_command(["-s", device_id, "shell", "pkill", "-2", "screenrecord"])
            import time as time_module
            time_module.sleep(1)  # Give it time to save
        
        # Pull the file from device
        console.print("[yellow]Downloading recording...[/yellow]")
        _, stderr, code = device_manager.adb._run_command([
            "-s", device_id, "pull", temp_file, filepath
        ])
        
        if code == 0:
            console.print(f"[green]✓ Recording saved to: {filepath}[/green]")
            
            # Clean up temp file on device
            device_manager.adb._run_command(["-s", device_id, "shell", "rm", temp_file])
        else:
            console.print(f"[red]Failed to download recording: {stderr}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@main.command()
@click.option('-d', '--device', help='Device to disconnect (defaults to selection prompt)')
@click.pass_context
def disconnect(ctx, device):
    """Disconnect a device (wireless connections only)"""
    device_manager = ctx.obj['device_manager']
    
    try:
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices connected[/yellow]")
            return
        
        # Filter for wireless devices (those with IP addresses)
        wireless_devices = [d for d in devices if ':' in d['id'] and '.' in d['id']]
        
        if not wireless_devices:
            console.print("[yellow]No wireless devices to disconnect[/yellow]")
            console.print("Note: USB devices disconnect when unplugged")
            return
        
        if device:
            target_device = device
        else:
            # Show selection
            from rich.prompt import Prompt
            console.print("\n[bold]Wireless devices:[/bold]")
            for i, dev in enumerate(wireless_devices, 1):
                console.print(f"{i}. {dev['id']} ({dev.get('model', 'Unknown')})")
            
            choice = Prompt.ask("\nSelect device to disconnect", 
                              choices=[str(i) for i in range(1, len(wireless_devices) + 1)])
            target_device = wireless_devices[int(choice) - 1]['id']
        
        # Disconnect
        stdout, stderr, code = device_manager.adb._run_command(["disconnect", target_device])
        
        if code == 0:
            console.print(f"[green]✓ Disconnected {target_device}[/green]")
        else:
            console.print(f"[red]Failed to disconnect: {stderr or stdout}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@add_device.command('pair')
@click.option('-d', '--discover', is_flag=True, help='Discover devices ready for pairing')
@click.pass_context  
def pair(ctx, discover):
    """Pair a device using WiFi (manual pairing)"""
    device_manager = ctx.obj['device_manager']
    
    try:
        pairing = WiFiPairing(device_manager.adb)
        
        if discover:
            # Discovery mode - find devices advertising pairing
            discovery = MDNSDiscovery()
            devices = discovery.start_discovery(timeout=20)
            
            selected_device = discovery.display_discovered_devices(devices)
            if not selected_device:
                return
            
            console.print(f"\n[bold]Selected device at {selected_device['addresses'][0]}:{selected_device['port']}[/bold]")
            console.print("\nNow get the pairing code from your device and continue with manual pairing.\n")
            
            # Continue to manual pairing with pre-filled IP:port
            ip_port = f"{selected_device['addresses'][0]}:{selected_device['port']}"
            console.print(f"[dim]Using pairing address: {ip_port}[/dim]\n")
        else:
            ip_port = None
        
        # Manual pairing
        from rich.prompt import Prompt
        
        console.print("[bold]Manual WiFi Pairing[/bold]\n")
        console.print("Follow these steps on your Android device:")
        console.print("1. Go to Settings → Developer Options → Wireless debugging")
        console.print("2. Tap 'Pair device with pairing code'")
        console.print("3. Note the IP address, port, and 6-digit code shown\n")
        
        if not ip_port:
            ip_port = Prompt.ask("Enter the pairing address (IP:port)")
        
        pairing_code = Prompt.ask("Enter the 6-digit pairing code")
        
        console.print(f"\n[yellow]Attempting to pair with {ip_port}...[/yellow]")
        
        success, message = pairing.pair_device(ip_port, pairing_code)
        
        if success:
            console.print(f"[green]✓ Successfully paired![/green]")
            console.print("\nTo connect to the device, use:")
            console.print(f"[cyan]adbh connect {ip_port.split(':')[0]}:5555[/cyan]")
        else:
            console.print(f"[red]✗ Pairing failed: {message}[/red]")
            console.print("\nTroubleshooting:")
            console.print("• Make sure the pairing code hasn't expired (they're only valid for a short time)")
            console.print("• Verify both devices are on the same network")
            console.print("• Check that you entered the pairing port (not the connection port)")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Pairing cancelled[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@add_device.command('qrcode')
@click.option('--experimental', is_flag=True, help='Try experimental SPAKE2 implementation')
def qrcode(experimental):
    """Show QR code pairing info (experimental)"""
    
    if experimental:
        console.print("\n[bold red]⚠️  EXPERIMENTAL SPAKE2 QR Code Pairing[/bold red]")
        console.print("This attempts to implement the SPAKE2 protocol.")
        console.print("[yellow]This is highly experimental and may not work![/yellow]\n")
        
        from rich.prompt import Prompt
        if Prompt.ask("Continue with experimental pairing?", choices=["y", "n"], default="n") == "y":
            try:
                from .core.pairing import WiFiPairing
                from .core.spake2_pairing import SPAKE2PairingServer
                from .core.mdns_pairing import MDNSPairingService
                
                adb = ADBWrapper()
                pairing = WiFiPairing(adb)
                
                # Generate pairing info
                pairing_info = pairing.start_pairing_session(use_mdns=False)
                if not pairing_info:
                    return
                
                # Start SPAKE2 server
                spake2_server = SPAKE2PairingServer(
                    session_name=pairing_info["session"],
                    pairing_code=pairing_info["code"]
                )
                
                if not spake2_server.start():
                    return
                
                # Start mDNS service pointing to SPAKE2 server
                mdns_service = MDNSPairingService(
                    session_name=pairing_info["session"],
                    pairing_code=pairing_info["code"],
                    port=spake2_server.port
                )
                
                if not mdns_service.start(advertise_only=True):
                    spake2_server.stop()
                    return
                
                console.print(f"\n[bold]Experimental SPAKE2 Server Running[/bold]")
                console.print(f"Port: {spake2_server.port}")
                console.print("\n[yellow]Waiting for device to pair...[/yellow]")
                console.print("[dim]Press Ctrl+C to cancel[/dim]\n")
                
                try:
                    paired_ip = spake2_server.wait_for_pairing(timeout=120)
                    
                    if paired_ip:
                        console.print(f"\n[green]✓ Device attempted pairing from {paired_ip}![/green]")
                        console.print("\n[yellow]Note: Full ADB protocol not implemented[/yellow]")
                        console.print("Try connecting with: [cyan]adbh connect <device-ip>:5555[/cyan]")
                    else:
                        console.print("\n[yellow]No devices paired[/yellow]")
                        
                except KeyboardInterrupt:
                    console.print("\n[yellow]Pairing cancelled[/yellow]")
                    
                finally:
                    spake2_server.stop()
                    mdns_service.stop()
                    
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
    else:
        console.print("\n[bold yellow]⚠️  QR Code Pairing Information[/bold yellow]")
        console.print("Full QR code pairing requires the SPAKE2 protocol with TLS.")
        console.print("This is complex and only partially implemented.\n")
        
        console.print("[bold]Options:[/bold]")
        console.print("1. [cyan]adbh pair[/cyan] - Manual pairing (recommended)")
        console.print("2. [cyan]adbh pair --discover[/cyan] - Find devices ready to pair")
        console.print("3. [cyan]adbh qrcode --experimental[/cyan] - Try experimental SPAKE2 (may not work)")
        
        from rich.prompt import Prompt
        if Prompt.ask("\nShow QR code for reference?", choices=["y", "n"], default="n") == "y":
            try:
                adb = ADBWrapper()
                pairing = WiFiPairing(adb)
                pairing_info = pairing.start_pairing_session(use_mdns=False)
                
                console.print("\n[dim]Note: This QR code is for reference only.[/dim]")
                console.print("[dim]Use --experimental flag to try SPAKE2 implementation.[/dim]")
                
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()