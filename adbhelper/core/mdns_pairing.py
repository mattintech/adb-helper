"""mDNS service for WiFi pairing with QR code support"""

import socket
import threading
import time
import json
from typing import Optional, Callable
from zeroconf import ServiceInfo, Zeroconf
from rich.console import Console

console = Console()

class MDNSPairingService:
    """Handles mDNS advertisement for ADB pairing"""
    
    def __init__(self, session_name: str, pairing_code: str, port: int = 0):
        self.session_name = session_name
        self.pairing_code = pairing_code
        self.port = port or self._find_free_port()
        self.zeroconf = None
        self.service_info = None
        self.server_thread = None
        self.running = False
        self.paired_callback = None
        
    def _find_free_port(self) -> int:
        """Find a free port for the pairing service"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def _get_local_ip(self) -> str:
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
    
    def start(self, paired_callback: Optional[Callable] = None, advertise_only: bool = False) -> bool:
        """Start the mDNS service and optionally a pairing server
        
        Args:
            paired_callback: Callback when device pairs
            advertise_only: If True, only advertise mDNS without starting a server
        """
        try:
            self.paired_callback = paired_callback
            
            # Start the pairing server only if not in advertise-only mode
            if not advertise_only:
                self.running = True
                self.server_thread = threading.Thread(target=self._run_pairing_server)
                self.server_thread.daemon = True
                self.server_thread.start()
            
            # Register mDNS service
            self.zeroconf = Zeroconf()
            
            # Create service info for ADB pairing
            # Service type: _adb-tls-pairing._tcp.local.
            service_type = "_adb-tls-pairing._tcp.local."
            service_name = f"{self.session_name}.{service_type}"
            
            local_ip = self._get_local_ip()
            
            # Properties for the service
            properties = {
                'name': self.session_name.encode('utf-8'),
                'code': self.pairing_code.encode('utf-8'),
            }
            
            self.service_info = ServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=properties,
                server=f"{self.session_name}.local.",
            )
            
            self.zeroconf.register_service(self.service_info)
            
            console.print(f"[green]✓ mDNS service started[/green]")
            console.print(f"  Service: {self.session_name}")
            console.print(f"  IP: {local_ip}:{self.port}")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to start mDNS service: {e}[/red]")
            return False
    
    def _run_pairing_server(self):
        """Run the pairing server that handles incoming connections"""
        # Don't run a server if we're just advertising for another service
        if not self.running:
            return
            
        # This is a placeholder - in the experimental mode, the SPAKE2 server handles connections
        pass
    
    def stop(self):
        """Stop the mDNS service and pairing server"""
        self.running = False
        
        if self.service_info and self.zeroconf:
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
            except:
                pass
        
        if self.server_thread:
            self.server_thread.join(timeout=2)
        
        console.print("[yellow]mDNS service stopped[/yellow]")
    
    def wait_for_pairing(self, timeout: int = 120) -> bool:
        """Wait for a device to pair"""
        start_time = time.time()
        
        try:
            while self.running and (time.time() - start_time) < timeout:
                time.sleep(0.5)
                
            return True
            
        except KeyboardInterrupt:
            return False