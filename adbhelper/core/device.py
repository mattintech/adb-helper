"""Device management and selection"""

from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from .adb import ADBWrapper, ADBError

console = Console()

class DeviceManager:
    """Manage multiple Android devices"""
    
    def __init__(self):
        self.adb = ADBWrapper()
        self._selected_device = None
    
    def list_devices(self) -> List[dict]:
        """Get list of all connected devices"""
        return self.adb.get_devices()
    
    def get_device_count(self) -> int:
        """Get number of connected devices"""
        devices = self.list_devices()
        return len([d for d in devices if d["status"] == "device"])
    
    def select_device(self, device_id: Optional[str] = None) -> Optional[str]:
        """Select a device for operations"""
        devices = [d for d in self.list_devices() if d["status"] == "device"]
        
        if not devices:
            console.print("[red]No devices connected![/red]")
            return None
        
        if device_id:
            # Verify the specified device exists
            if any(d["id"] == device_id for d in devices):
                self._selected_device = device_id
                return device_id
            else:
                console.print(f"[red]Device {device_id} not found![/red]")
                return None
        
        if len(devices) == 1:
            # Auto-select if only one device
            self._selected_device = devices[0]["id"]
            return self._selected_device
        
        # Show device selector
        return self._interactive_device_selection(devices)
    
    def _interactive_device_selection(self, devices: List[dict]) -> Optional[str]:
        """Interactive device selection UI"""
        table = Table(title="Connected Devices")
        table.add_column("Index", style="cyan", no_wrap=True)
        table.add_column("Device ID", style="green")
        table.add_column("Model", style="yellow")
        table.add_column("Status", style="magenta")
        
        for idx, device in enumerate(devices, 1):
            table.add_row(
                str(idx),
                device["id"],
                device.get("model", "Unknown"),
                device["status"]
            )
        
        console.print(table)
        
        while True:
            choice = Prompt.ask(
                "Select device by index",
                choices=[str(i) for i in range(1, len(devices) + 1)],
                default="1"
            )
            
            try:
                idx = int(choice) - 1
                self._selected_device = devices[idx]["id"]
                return self._selected_device
            except (ValueError, IndexError):
                console.print("[red]Invalid selection![/red]")
    
    def get_selected_device(self) -> Optional[str]:
        """Get currently selected device"""
        return self._selected_device
    
    def get_device_info(self, device_id: Optional[str] = None) -> dict:
        """Get detailed device information"""
        device_id = device_id or self._selected_device
        if not device_id:
            raise ADBError("No device selected")
        
        # Get user-defined device name from settings
        try:
            stdout, stderr, code = self.adb._run_command(["-s", device_id, "shell", "settings get global device_name"])
            device_name = stdout.strip() if code == 0 and stdout.strip() != "null" else None
        except:
            device_name = None
        
        info = {
            "id": device_id,
            "device_name": device_name,
            "serial": self.adb.get_device_property("ro.serialno", device_id),
            "manufacturer": self.adb.get_device_property("ro.product.manufacturer", device_id),
            "model": self.adb.get_device_property("ro.product.model", device_id),
            "android_version": self.adb.get_device_property("ro.build.version.release", device_id),
            "sdk_version": self.adb.get_device_property("ro.build.version.sdk", device_id),
            "build_type": self.adb.get_device_property("ro.build.type", device_id),
        }
        
        return info
    
    def ensure_device_ready(self, device_id: Optional[str] = None) -> str:
        """Ensure a device is selected and ready"""
        device_id = device_id or self._selected_device
        
        if not device_id:
            device_id = self.select_device()
            
        if not device_id:
            raise ADBError("No device available")
        
        # Verify device is still connected
        devices = self.list_devices()
        if not any(d["id"] == device_id and d["status"] == "device" for d in devices):
            raise ADBError(f"Device {device_id} is not ready")
        
        return device_id