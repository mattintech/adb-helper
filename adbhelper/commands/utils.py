"""Utility functions for command operations"""
from typing import List, Optional
from rich.console import Console
from rich.prompt import Prompt
from ..core.device import DeviceManager

console = Console()


class DeviceSelector:
    """Handles device selection logic for commands"""
    
    @staticmethod
    def select_single_device(device_manager: DeviceManager, device_id: Optional[str] = None) -> Optional[str]:
        """Select a single device, either specified or from prompt"""
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices found[/yellow]")
            return None
        
        if device_id:
            # Verify specified device exists
            if not any(d['id'] == device_id for d in devices):
                console.print(f"[red]Device {device_id} not found[/red]")
                return None
            return device_id
        
        # Use device_manager's selection logic
        return device_manager.select_device(None)
    
    @staticmethod
    def select_multiple_devices(device_manager: DeviceManager, device_id: Optional[str] = None) -> List[str]:
        """Select one or more devices for operations"""
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices found[/yellow]")
            return []
        
        # If specific device is provided, use it
        if device_id:
            # Verify device exists
            if not any(d['id'] == device_id for d in devices):
                console.print(f"[red]Device {device_id} not found[/red]")
                return []
            return [device_id]
        
        # Interactive device selection
        if len(devices) == 1:
            # Only one device, use it
            console.print(f"Using device: [green]{devices[0]['id']}[/green] ({devices[0].get('model', 'Unknown')})")
            return [devices[0]['id']]
        
        # Multiple devices - ask for mode
        console.print("\n[bold]Device Selection:[/bold]")
        console.print("1. Single device")
        console.print("2. Multiple devices")
        console.print("3. All devices\n")
        
        mode = Prompt.ask("Select mode", choices=["1", "2", "3"], default="1")
        
        if mode == "1":
            # Single device selection
            device_id = device_manager.select_device(None)
            return [device_id] if device_id else []
            
        elif mode == "2":
            # Multiple device selection
            console.print("\n[bold]Select devices (comma-separated numbers):[/bold]")
            for i, dev in enumerate(devices, 1):
                console.print(f"{i}. {dev['id']} ({dev.get('model', 'Unknown')})")
            
            selections = Prompt.ask("\nDevices to use").split(',')
            target_devices = []
            
            for sel in selections:
                try:
                    idx = int(sel.strip()) - 1
                    if 0 <= idx < len(devices):
                        target_devices.append(devices[idx]['id'])
                    else:
                        console.print(f"[yellow]Skipping invalid selection: {sel}[/yellow]")
                except ValueError:
                    console.print(f"[yellow]Skipping invalid selection: {sel}[/yellow]")
            
            return target_devices
                
        else:  # mode == "3"
            # All devices
            console.print(f"[green]Using all {len(devices)} device(s)[/green]")
            return [d['id'] for d in devices]