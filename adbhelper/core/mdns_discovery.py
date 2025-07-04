"""mDNS discovery for Android devices advertising pairing"""

import time
from typing import List, Dict, Optional
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo
from rich.console import Console
from rich.table import Table

console = Console()

class ADBPairingListener(ServiceListener):
    """Listener for ADB pairing services advertised via mDNS"""
    
    def __init__(self):
        self.services = {}
        
    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is discovered"""
        info = zeroconf.get_service_info(service_type, name)
        if info:
            # Extract device info
            device_info = {
                'name': name,
                'server': info.server,
                'port': info.port,
                'addresses': [addr for addr in info.parsed_addresses()],
                'properties': info.properties,
            }
            
            # Parse the instance name to get device ID
            # Format: adb-{device_id}-{random}._adb-tls-pairing._tcp.local.
            if name.startswith('adb-'):
                parts = name.split('-')
                if len(parts) >= 3:
                    device_info['device_id'] = parts[1]
            
            self.services[name] = device_info
            console.print(f"[green]✓ Found device:[/green] {info.server} at {device_info['addresses'][0]}:{info.port}")
    
    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is removed"""
        if name in self.services:
            del self.services[name]
    
    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is updated"""
        pass

class MDNSDiscovery:
    """Discover Android devices advertising for pairing"""
    
    def __init__(self):
        self.zeroconf = None
        self.browser = None
        self.listener = None
    
    def start_discovery(self, timeout: int = 30) -> List[Dict]:
        """Start discovering devices advertising pairing"""
        console.print("\n[bold]Discovering Android devices ready for pairing...[/bold]")
        console.print("[dim]Make sure your device has 'Pair device with pairing code' dialog open[/dim]\n")
        
        self.zeroconf = Zeroconf()
        self.listener = ADBPairingListener()
        
        # Browse for ADB pairing services
        service_type = "_adb-tls-pairing._tcp.local."
        self.browser = ServiceBrowser(self.zeroconf, service_type, self.listener)
        
        # Wait for discovery
        start_time = time.time()
        last_count = 0
        
        try:
            while (time.time() - start_time) < timeout:
                current_count = len(self.listener.services)
                
                # Show progress
                if current_count != last_count:
                    console.print(f"[yellow]Found {current_count} device(s)...[/yellow]")
                    last_count = current_count
                
                time.sleep(1)
                
                # Check if user wants to stop early
                if current_count > 0 and (time.time() - start_time) > 5:
                    console.print("\n[dim]Press Ctrl+C to stop searching and use found devices[/dim]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Discovery stopped by user[/yellow]")
        
        finally:
            self.stop_discovery()
        
        return list(self.listener.services.values())
    
    def stop_discovery(self):
        """Stop the discovery process"""
        if self.browser:
            self.browser.cancel()
        if self.zeroconf:
            self.zeroconf.close()
    
    def display_discovered_devices(self, devices: List[Dict]) -> Optional[Dict]:
        """Display discovered devices and let user select one"""
        if not devices:
            console.print("[yellow]No devices found advertising pairing[/yellow]")
            console.print("\nMake sure on your Android device:")
            console.print("1. Wireless debugging is enabled")
            console.print("2. You've tapped 'Pair device with pairing code'")
            console.print("3. The pairing dialog is still open")
            return None
        
        # Create table
        table = Table(title="Devices Ready for Pairing")
        table.add_column("Index", style="cyan")
        table.add_column("Device", style="green")
        table.add_column("IP Address", style="yellow")
        table.add_column("Port", style="magenta")
        
        for idx, device in enumerate(devices, 1):
            ip = device['addresses'][0] if device['addresses'] else 'Unknown'
            table.add_row(
                str(idx),
                device.get('device_id', device['server']),
                ip,
                str(device['port'])
            )
        
        console.print(table)
        
        if len(devices) == 1:
            console.print(f"\n[green]Using the only device found[/green]")
            return devices[0]
        
        # Let user select
        from rich.prompt import Prompt
        
        while True:
            choice = Prompt.ask(
                "\nSelect device by index",
                choices=[str(i) for i in range(1, len(devices) + 1)],
                default="1"
            )
            
            try:
                idx = int(choice) - 1
                return devices[idx]
            except (ValueError, IndexError):
                console.print("[red]Invalid selection![/red]")