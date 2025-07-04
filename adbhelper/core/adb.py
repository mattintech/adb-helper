"""Core ADB wrapper functionality"""

import subprocess
import shutil
from typing import List, Optional, Tuple
from rich.console import Console

console = Console()

class ADBError(Exception):
    """Custom exception for ADB-related errors"""
    pass

class ADBWrapper:
    """Wrapper for Android Debug Bridge commands"""
    
    def __init__(self):
        self.adb_path = self._find_adb()
        
    def _find_adb(self) -> str:
        """Find ADB executable in system PATH"""
        adb_path = shutil.which("adb")
        if not adb_path:
            raise ADBError("ADB not found in PATH. Please install Android SDK Platform Tools.")
        return adb_path
    
    def _run_command(self, args: List[str], device_id: Optional[str] = None) -> Tuple[str, str, int]:
        """Run an ADB command and return output"""
        cmd = [self.adb_path]
        
        if device_id:
            cmd.extend(["-s", device_id])
            
        cmd.extend(args)
        
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return process.stdout, process.stderr, process.returncode
        except subprocess.TimeoutExpired:
            raise ADBError(f"ADB command timed out: {' '.join(cmd)}")
        except Exception as e:
            raise ADBError(f"Failed to run ADB command: {e}")
    
    def get_devices(self) -> List[dict]:
        """Get list of connected devices"""
        stdout, stderr, code = self._run_command(["devices", "-l"])
        
        if code != 0:
            raise ADBError(f"Failed to get devices: {stderr}")
        
        devices = []
        lines = stdout.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            if not line.strip():
                continue
                
            parts = line.split()
            if len(parts) >= 2:
                device_id = parts[0]
                status = parts[1]
                
                # Parse additional device info
                device_info = {
                    "id": device_id,
                    "status": status,
                    "model": None,
                    "device": None,
                    "transport_id": None,
                    "transport_type": None
                }
                
                # Determine transport type based on device ID format
                if ':' in device_id and '.' in device_id:
                    # IP:port format indicates WiFi connection
                    device_info["transport_type"] = "WiFi"
                else:
                    # Otherwise it's USB
                    device_info["transport_type"] = "USB"
                
                # Extract additional properties
                for part in parts[2:]:
                    if part.startswith("model:"):
                        device_info["model"] = part.split(":")[1]
                    elif part.startswith("device:"):
                        device_info["device"] = part.split(":")[1]
                    elif part.startswith("transport_id:"):
                        device_info["transport_id"] = part.split(":")[1]
                
                devices.append(device_info)
        
        return devices
    
    def get_device_property(self, property_name: str, device_id: Optional[str] = None) -> str:
        """Get a device property"""
        stdout, stderr, code = self._run_command(
            ["shell", "getprop", property_name], 
            device_id
        )
        
        if code != 0:
            raise ADBError(f"Failed to get property {property_name}: {stderr}")
        
        return stdout.strip()
    
    def shell(self, command: str, device_id: Optional[str] = None) -> Tuple[str, str, int]:
        """Execute shell command on device"""
        return self._run_command(["shell", command], device_id)
    
    def push(self, local_path: str, remote_path: str, device_id: Optional[str] = None) -> bool:
        """Push file to device"""
        stdout, stderr, code = self._run_command(
            ["push", local_path, remote_path], 
            device_id
        )
        return code == 0
    
    def pull(self, remote_path: str, local_path: str, device_id: Optional[str] = None) -> bool:
        """Pull file from device"""
        stdout, stderr, code = self._run_command(
            ["pull", remote_path, local_path], 
            device_id
        )
        return code == 0
    
    def is_available(self) -> bool:
        """Check if ADB is available and working"""
        try:
            stdout, stderr, code = self._run_command(["version"])
            return code == 0
        except:
            return False