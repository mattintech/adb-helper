"""Command registration module"""
import click
import subprocess
import os
import sys
import time
import platform
import webbrowser
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from ..core.adb import ADBWrapper, ADBError
from ..core.device import DeviceManager
from ..core.pairing import WiFiPairing
from ..core.mdns_discovery import MDNSDiscovery
from ..core.connection_history import ConnectionHistory
from .utils import DeviceSelector

console = Console()


def register_commands(main_group):
    """Register all commands with the main CLI group"""
    
    # Basic commands
    @main_group.command()
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
    
    @main_group.command()
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
    
    @main_group.command()
    @click.option('-d', '--device', help='Target device ID')
    @click.pass_context
    def info(ctx, device):
        """Show detailed device information"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            info = device_manager.get_device_info(device_id)
            
            console.print(f"\n[bold]Device Information[/bold]")
            console.print(f"ID: [green]{info['id']}[/green]")
            if info.get('device_name') and info['device_name'] != "Unknown":
                console.print(f"Device Name: [bold cyan]{info['device_name']}[/bold cyan]")
            console.print(f"Serial Number: [yellow]{info['serial']}[/yellow]")
            console.print(f"Manufacturer: [cyan]{info['manufacturer']}[/cyan]")
            console.print(f"Model: [cyan]{info['model']}[/cyan]")
            console.print(f"Android Version: [yellow]{info['android_version']}[/yellow]")
            console.print(f"SDK Version: [yellow]{info['sdk_version']}[/yellow]")
            console.print(f"Build Type: [magenta]{info['build_type']}[/magenta]")
            
        except ADBError as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @main_group.command()
    @click.argument('shell_command', nargs=-1, required=False)
    @click.option('-d', '--device', help='Target specific device ID')
    @click.option('-a', '--all', 'all_devices', is_flag=True, help='Run on all connected devices')
    @click.option('-m', '--multi', is_flag=True, help='Select multiple devices interactively')
    @click.pass_context
    def shell(ctx, shell_command, device, all_devices, multi):
        """Run shell commands on one or more devices"""
        device_manager = ctx.obj['device_manager']
        
        try:
            devices = device_manager.list_devices()
            if not devices:
                console.print("[yellow]No devices connected[/yellow]")
                return
            
            # Determine which devices to use
            target_devices = []
            
            if all_devices:
                # Use all connected devices
                target_devices = [d['id'] for d in devices if d['status'] == 'device']
                console.print(f"[cyan]Running on all {len(target_devices)} devices[/cyan]")
            elif multi:
                # Let user select multiple devices
                console.print("[bold]Select devices (space to toggle, enter to confirm):[/bold]")
                
                # Show devices with checkboxes
                from rich.prompt import Prompt
                table = Table(show_header=True)
                table.add_column("#", style="cyan", width=3)
                table.add_column("Device ID", style="green")
                table.add_column("Model", style="yellow")
                
                for idx, device in enumerate(devices, 1):
                    if device['status'] == 'device':
                        table.add_row(
                            str(idx),
                            device['id'],
                            device.get('model', 'Unknown')
                        )
                
                console.print(table)
                
                # Get comma-separated list of device numbers
                selection = Prompt.ask("Enter device numbers (comma-separated, e.g., 1,3,4)")
                selected_indices = [int(x.strip()) - 1 for x in selection.split(',') if x.strip().isdigit()]
                
                for idx in selected_indices:
                    if 0 <= idx < len(devices):
                        target_devices.append(devices[idx]['id'])
                
                if not target_devices:
                    console.print("[yellow]No devices selected[/yellow]")
                    return
            else:
                # Single device
                device_id = DeviceSelector.select_single_device(device_manager, device)
                if not device_id:
                    return
                target_devices = [device_id]
            
            if shell_command:
                # Run the provided command on all target devices
                cmd = ' '.join(shell_command)
                
                for device_id in target_devices:
                    console.print(f"\n[bold cyan]━━━ {device_id} ━━━[/bold cyan]")
                    console.print(f"[yellow]Running: {cmd}[/yellow]")
                    
                    stdout, stderr, code = device_manager.adb._run_command(["-s", device_id, "shell", cmd])
                    
                    if stdout:
                        console.print(stdout.rstrip())
                    if stderr:
                        console.print(f"[red]{stderr.rstrip()}[/red]")
                    
                    if code != 0:
                        console.print(f"[red]Command failed with exit code {code}[/red]")
                
                if len(target_devices) > 1:
                    console.print(f"\n[green]✓ Completed on {len(target_devices)} devices[/green]")
            else:
                # Interactive shell only works with single device
                if len(target_devices) > 1:
                    console.print("[red]Interactive shell only supports single device[/red]")
                    console.print("Use -d flag to select a specific device")
                    return
                
                device_id = target_devices[0]
                console.print(f"[green]Starting interactive shell on {device_id}[/green]")
                console.print("[dim]Type 'exit' to quit[/dim]\n")
                
                import subprocess
                subprocess.run([device_manager.adb.adb_path, "-s", device_id, "shell"])
                
        except ADBError as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @main_group.command()
    def enable_adb():
        """Interactive guide to enable ADB debugging"""
        # Get the path to the enable_adb_helper script
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts', 'enable_adb_helper.py')
        
        # Run the script with the current Python interpreter
        subprocess.run([sys.executable, script_path])
    
    @main_group.command()
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
    
    # Add device group
    @main_group.group(name='add-device', invoke_without_command=True)
    @click.pass_context
    def add_device(ctx):
        """Add devices via USB or wireless connection"""
        if ctx.invoked_subcommand is None:
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
        
        current_devices = device_manager.list_devices()
        if current_devices:
            console.print("\n[bold]Currently connected devices:[/bold]")
            for device in current_devices:
                console.print(f"  • {device['id']} ({device.get('model', 'Unknown')})")
        
        from ..scripts.enable_adb_helper import guide_usb_debugging
        
        console.print("\n[yellow]Make sure the new device is connected via USB and has USB debugging enabled[/yellow]")
        input("Press Enter when ready...")
        
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
            history = ConnectionHistory()
            
            if not address:
                console.print("\n[bold]Connect to WiFi Device[/bold]\n")
                
                # Show history and let user select
                selected = history.display_history_selection(connection_type="wireless")
                
                if selected == "NEW" or selected is None:
                    # Get subnet suggestion
                    subnet = ConnectionHistory.get_local_subnet()
                    if subnet:
                        console.print(f"[dim]Detected local network: {subnet}x[/dim]")
                        address = Prompt.ask("Enter device address (IP:port or just IP)", 
                                           default=subnet)
                        
                        # If user entered just the last octet(s), prepend the subnet
                        if address and '.' not in address:
                            address = subnet + address
                        elif address and address.count('.') < 3:
                            # Handle partial IPs
                            if address.startswith(subnet):
                                # User typed the full thing
                                pass
                            else:
                                # User typed partial, prepend subnet
                                address = subnet + address
                    else:
                        address = Prompt.ask("Enter device address (IP:port or just IP)")
                else:
                    address = selected
                    console.print(f"[green]Using {address} from history[/green]")
            
            if ':' not in address:
                # Ask for port instead of defaulting to 5555
                console.print("\n[bold]Note:[/bold] The wireless debugging port may vary.")
                console.print("Check your device's Wireless debugging screen for the port.\n")
                
                port = Prompt.ask("Enter the wireless debugging port", default="5555")
                address = f"{address}:{port}"
            
            console.print(f"\n[yellow]Connecting to {address}...[/yellow]")
            
            stdout, stderr, code = device_manager.adb._run_command(["connect", address])
            
            # Save to history regardless of success/failure (so user can retry easily)
            history.add_connection(address, connection_type="wireless")
            
            if code == 0 and "connected" in stdout.lower():
                console.print(f"[green]✓ Successfully connected to {address}![/green]")
                
                # Try to get device info and update history with device name
                try:
                    # Extract device ID from address for device info
                    device_info = device_manager.get_device_info(address)
                    # Prefer user-defined device name, fall back to manufacturer/model
                    device_name = device_info.get('device_name')
                    if not device_name:
                        device_name = f"{device_info.get('manufacturer', '')} {device_info.get('model', '')}".strip()
                    if device_name:
                        ip = address.split(':')[0]
                        history.update_device_name(ip, device_name)
                        console.print(f"[dim]Device: {device_name}[/dim]")
                except Exception:
                    # Ignore errors getting device info
                    pass
                
                console.print("\nRun [cyan]adbh devices[/cyan] to see connected devices")
            else:
                console.print(f"[red]✗ Failed to connect: {stderr or stdout}[/red]")
                
                # Check if it's a connection refused error suggesting pairing is needed
                if "refused" in (stderr or stdout).lower() or "failed" in (stderr or stdout).lower():
                    console.print("\n[yellow]The device may need to be paired first.[/yellow]")
                    
                    if Prompt.ask("Would you like to pair the device now?", choices=["y", "n"], default="y") == "y":
                        # Extract IP from address
                        ip = address.split(':')[0]
                        console.print(f"\n[cyan]Starting pairing process for {ip}...[/cyan]\n")
                        
                        # Call the pair function directly
                        ctx.invoke(pair, address=ip, pairing_code=None, discover=False)
                        return
                
                console.print("\nTroubleshooting:")
                console.print("• Make sure the device has wireless debugging enabled")
                console.print("• Verify both devices are on the same network")
                console.print("• Try pairing first: [cyan]adbh add-device pair[/cyan]")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @add_device.command('pair')
    @click.argument('address', required=False)
    @click.argument('pairing_code', required=False)
    @click.option('-d', '--discover', is_flag=True, help='Discover devices ready for pairing')
    @click.pass_context
    def pair(ctx, address, pairing_code, discover):
        """Pair a device using WiFi (manual pairing)"""
        device_manager = ctx.obj['device_manager']
        
        try:
            pairing = WiFiPairing(device_manager.adb)
            history = ConnectionHistory()
            
            if discover:
                discovery = MDNSDiscovery()
                devices = discovery.start_discovery(timeout=20)
                
                selected_device = discovery.display_discovered_devices(devices)
                if not selected_device:
                    return
                
                console.print(f"\n[bold]Selected device at {selected_device['addresses'][0]}:{selected_device['port']}[/bold]")
                console.print("\nNow get the pairing code from your device and continue with manual pairing.\n")
                
                ip_port = f"{selected_device['addresses'][0]}:{selected_device['port']}"
                console.print(f"[dim]Using pairing address: {ip_port}[/dim]\n")
            else:
                ip_port = None
            
            # Handle command line arguments
            if address:
                ip_port = address
            else:
                ip_port = None
            
            console.print("[bold]Manual WiFi Pairing[/bold]\n")
            console.print("Follow these steps on your Android device:")
            console.print("1. Go to Settings → Developer Options → Wireless debugging")
            console.print("2. Tap 'Pair device with pairing code'")
            console.print("3. Note the IP address, port, and 6-digit code shown\n")
            
            # If no address provided at all, check history or ask for it
            if not ip_port:
                # Show history and let user select
                selected = history.display_history_selection(connection_type="pairing")
                
                if selected == "NEW" or selected is None:
                    # Get subnet suggestion
                    subnet = ConnectionHistory.get_local_subnet()
                    if subnet:
                        console.print(f"[dim]Detected local network: {subnet}x[/dim]")
                        ip_port = Prompt.ask("Enter the pairing address (IP:port or just IP)", 
                                           default=subnet)
                        
                        # If user entered just the last octet(s), prepend the subnet
                        if ip_port and '.' not in ip_port:
                            ip_port = subnet + ip_port
                        elif ip_port and ip_port.count('.') < 3:
                            # Handle partial IPs like "100.143" when subnet is "172.16."
                            if ip_port.startswith(subnet):
                                # User typed the full thing
                                pass
                            else:
                                # User typed partial, prepend subnet
                                ip_port = subnet + ip_port
                    else:
                        ip_port = Prompt.ask("Enter the pairing address (IP:port or just IP)")
                else:
                    ip_port = selected
                    console.print(f"[green]Using {ip_port} from history[/green]")
            
            # If IP provided without port, ask for port
            if ':' not in ip_port:
                port = Prompt.ask("Enter the pairing port")
                ip_port = f"{ip_port}:{port}"
            
            # If no pairing code provided, ask for it
            if not pairing_code:
                pairing_code = Prompt.ask("Enter the 6-digit pairing code")
            
            console.print(f"\n[yellow]Attempting to pair with {ip_port}...[/yellow]")
            
            success, message = pairing.pair_device(ip_port, pairing_code)
            
            if success:
                console.print(f"[green]✓ Successfully paired![/green]")
                
                # Save to history
                history.add_connection(ip_port, connection_type="pairing")
                
                # Ask if user wants to connect now
                if Prompt.ask("\nConnect to the device now?", choices=["y", "n"], default="y") == "y":
                    console.print("\n[bold]Note:[/bold] The connection port is different from the pairing port.")
                    console.print("Check your device's Wireless debugging screen for the IP address and port.\n")
                    
                    connect_port = Prompt.ask("Enter the connection port", default="5555")
                    connect_ip = f"{ip_port.split(':')[0]}:{connect_port}"
                    
                    console.print(f"\n[yellow]Connecting to {connect_ip}...[/yellow]")
                    
                    stdout, stderr, code = device_manager.adb._run_command(["connect", connect_ip])
                    
                    # Save wireless connection to history regardless of success
                    history.add_connection(connect_ip, connection_type="wireless")
                    
                    if code == 0 and "connected" in stdout.lower():
                        console.print(f"[green]✓ Successfully connected to {connect_ip}![/green]")
                        
                        # Try to get device info and update history with device name
                        try:
                            device_info = device_manager.get_device_info(connect_ip)
                            # Prefer user-defined device name, fall back to manufacturer/model
                            device_name = device_info.get('device_name')
                            if not device_name:
                                device_name = f"{device_info.get('manufacturer', '')} {device_info.get('model', '')}".strip()
                            if device_name:
                                ip = connect_ip.split(':')[0]
                                history.update_device_name(ip, device_name)
                                console.print(f"[dim]Device: {device_name}[/dim]")
                        except Exception:
                            # Ignore errors getting device info
                            pass
                        
                        console.print("\nRun [cyan]adbh devices[/cyan] to see connected devices")
                    else:
                        console.print(f"[red]✗ Failed to connect: {stderr or stdout}[/red]")
                        console.print(f"\nYou can try connecting manually with:")
                        console.print(f"[cyan]adbh add-device wireless {ip_port.split(':')[0]}:<port>[/cyan]")
                else:
                    console.print("\nTo connect to the device later, use:")
                    console.print(f"[cyan]adbh add-device wireless {ip_port.split(':')[0]}:<port>[/cyan]")
                    console.print("(Check your device's Wireless debugging screen for the port)")
            else:
                console.print(f"[red]✗ Pairing failed: {message}[/red]")
                console.print("\nTroubleshooting:")
                console.print("• Make sure the pairing code hasn't expired")
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
            
            if Prompt.ask("Continue with experimental pairing?", choices=["y", "n"], default="n") == "y":
                try:
                    from ..core.spake2_pairing import SPAKE2PairingServer
                    from ..core.mdns_pairing import MDNSPairingService
                    
                    adb = ADBWrapper()
                    pairing = WiFiPairing(adb)
                    
                    pairing_info = pairing.start_pairing_session(use_mdns=False)
                    if not pairing_info:
                        return
                    
                    spake2_server = SPAKE2PairingServer(
                        session_name=pairing_info["session"],
                        pairing_code=pairing_info["code"]
                    )
                    
                    if not spake2_server.start():
                        return
                    
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
            
            if Prompt.ask("\nShow QR code for reference?", choices=["y", "n"], default="n") == "y":
                try:
                    adb = ADBWrapper()
                    pairing = WiFiPairing(adb)
                    pairing_info = pairing.start_pairing_session(use_mdns=False)
                    
                    console.print("\n[dim]Note: This QR code is for reference only.[/dim]")
                    console.print("[dim]Use --experimental flag to try SPAKE2 implementation.[/dim]")
                    
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
    
    # Register capture and log command groups
    from .capture_commands import register_capture_commands
    from .log_commands import register_log_commands
    from .app_commands import register_app_commands
    
    register_capture_commands(main_group)
    register_log_commands(main_group)
    register_app_commands(main_group)