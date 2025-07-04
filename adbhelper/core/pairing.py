"""WiFi pairing functionality with QR code support"""

import io
import random
import string
import socket
import threading
from typing import Optional, Tuple
import qrcode
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.prompt import Prompt
from .adb import ADBWrapper, ADBError
from .mdns_pairing import MDNSPairingService

console = Console()

class WiFiPairing:
    """Handle WiFi pairing with QR code generation"""
    
    def __init__(self, adb: ADBWrapper):
        self.adb = adb
        
    def generate_pairing_code(self) -> str:
        """Generate a 6-digit pairing code"""
        return ''.join(random.choices(string.digits, k=6))
    
    def get_local_ip(self) -> str:
        """Get the local IP address"""
        try:
            # Create a dummy socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def generate_qr_code(self, name: str, code: str) -> str:
        """Generate QR code data for WiFi pairing"""
        # Android expects this specific format for wireless debugging QR codes
        qr_data = f"WIFI:T:ADB;S:{name};P:{code};;"
        return qr_data
    
    def create_qr_image(self, qr_data: str) -> Image.Image:
        """Create a QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    
    def display_qr_terminal(self, qr_data: str) -> None:
        """Display QR code in terminal using Unicode blocks"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=1,
            border=2,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Get the QR code matrix
        matrix = qr.get_matrix()
        
        # Convert to Unicode block characters
        lines = []
        for row in matrix:
            line = ""
            for cell in row:
                line += "██" if cell else "  "
            lines.append(line)
        
        # Display in a nice panel
        qr_display = "\n".join(lines)
        panel = Panel(
            Align.center(qr_display),
            title="[bold cyan]Scan with Android Device[/bold cyan]",
            border_style="cyan"
        )
        console.print(panel)
    
    def pair_device(self, ip_port: str, pairing_code: str) -> Tuple[bool, str]:
        """Execute the pairing process"""
        try:
            # The pair command is interactive, so we need to handle it with subprocess
            import subprocess
            
            cmd = [self.adb.adb_path, "pair", ip_port]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send the pairing code
            stdout, stderr = process.communicate(input=pairing_code + "\n")
            
            if process.returncode == 0 and "Successfully paired" in stdout:
                return True, stdout
            else:
                return False, stderr or stdout
        except Exception as e:
            return False, str(e)
    
    def start_pairing_session(self, use_mdns: bool = True) -> Optional[dict]:
        """Start an interactive pairing session"""
        if not self.adb.supports_pairing():
            console.print("[red]Error: Your ADB version doesn't support wireless pairing.[/red]")
            console.print("Wireless pairing requires ADB version 30.0.0 or higher.")
            console.print(f"Your version: {self.adb.get_version() or 'Unknown'}")
            return None
        
        # Generate pairing info
        pairing_code = self.generate_pairing_code()
        local_ip = self.get_local_ip()
        session_name = f"adbhelper_{random.randint(1000, 9999)}"
        
        # Generate QR code
        qr_data = self.generate_qr_code(session_name, pairing_code)
        
        console.print(f"\n[bold]WiFi Pairing Setup[/bold]")
        console.print(f"• Session: [cyan]{session_name}[/cyan]")
        console.print(f"• Code: [green]{pairing_code}[/green]")
        console.print(f"• Your IP: [yellow]{local_ip}[/yellow]\n")
        
        # Display QR code
        self.display_qr_terminal(qr_data)
        
        console.print("\n[bold]On your Android device:[/bold]")
        console.print("1. Go to Settings → Developer Options → Wireless debugging")
        console.print("2. Tap 'Pair device with QR code'")
        console.print("3. Scan the QR code above\n")
        
        return {
            "code": pairing_code,
            "ip": local_ip,
            "session": session_name,
            "qr_data": qr_data
        }
    
    def start_pairing_with_mdns(self) -> Optional[str]:
        """Start pairing session with mDNS service"""
        pairing_info = self.start_pairing_session(use_mdns=True)
        if not pairing_info:
            return None
        
        # Start mDNS service
        mdns_service = MDNSPairingService(
            session_name=pairing_info["session"],
            pairing_code=pairing_info["code"]
        )
        
        paired_device_ip = None
        
        def on_paired(device_ip: str):
            nonlocal paired_device_ip
            paired_device_ip = device_ip
        
        if not mdns_service.start(paired_callback=on_paired):
            console.print("[red]Failed to start mDNS service[/red]")
            console.print("Try manual pairing instead: [cyan]adbh pair --manual[/cyan]")
            return None
        
        console.print("\n[yellow]Waiting for device to scan QR code...[/yellow]")
        console.print("[dim]Press Ctrl+C to cancel[/dim]\n")
        
        try:
            # Wait for pairing
            mdns_service.wait_for_pairing(timeout=120)
            
            if paired_device_ip:
                console.print(f"\n[green]✓ Device paired from {paired_device_ip}![/green]")
                console.print(f"\nTo connect, use: [cyan]adbh connect {paired_device_ip}:5555[/cyan]")
                return paired_device_ip
            else:
                console.print("\n[yellow]Pairing timed out[/yellow]")
                console.print("The device may still pair. Check your device and try:")
                console.print("[cyan]adbh devices[/cyan] to see if it connected")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Pairing cancelled[/yellow]")
            
        finally:
            mdns_service.stop()
        
        return None