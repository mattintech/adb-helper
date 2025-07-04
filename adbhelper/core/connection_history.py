"""Connection history management for ADB Helper"""

import json
import socket
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table

console = Console()


class ConnectionHistory:
    """Manages connection history for quick device selection"""
    
    @staticmethod
    def get_local_subnet() -> Optional[str]:
        """Get the local network subnet (e.g., '192.168.1.')"""
        try:
            # Create a socket to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Connect to an external IP (doesn't actually send data)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                # Get subnet (first 3 octets)
                parts = local_ip.split('.')
                if len(parts) == 4:
                    return f"{parts[0]}.{parts[1]}.{parts[2]}."
        except Exception:
            pass
        return None
    
    def __init__(self, history_file: Optional[str] = None):
        """Initialize connection history manager
        
        Args:
            history_file: Path to history file. Defaults to ~/.adbhelper_history.json
        """
        if history_file is None:
            self.history_file = Path.home() / ".adbhelper_history.json"
        else:
            self.history_file = Path(history_file)
        
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """Load history from file"""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                # Ensure we have a list
                if isinstance(data, list):
                    return data
                return []
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_history(self):
        """Save history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except IOError as e:
            console.print(f"[yellow]Warning: Could not save history: {e}[/yellow]")
    
    def add_connection(self, address: str, connection_type: str = "wireless", 
                      device_name: Optional[str] = None):
        """Add a connection to history
        
        Args:
            address: IP:port address
            connection_type: Type of connection (wireless, pairing)
            device_name: Optional device name/model
        """
        # Extract IP from address
        ip_only = address.split(':')[0] if ':' in address else address
        
        # Remove any existing entries with the same IP and type
        # This allows keeping both pairing and wireless entries for the same IP
        self.history = [h for h in self.history 
                       if not (h.get('ip') == ip_only and h.get('type') == connection_type)]
        
        # Add new entry
        entry = {
            'address': address,
            'ip': ip_only,
            'type': connection_type,
            'timestamp': datetime.now().isoformat(),
            'device_name': device_name
        }
        
        # Add to front of list
        self.history.insert(0, entry)
        
        # Keep only last 10 unique IPs
        seen_ips = set()
        filtered_history = []
        for item in self.history:
            if item['ip'] not in seen_ips:
                filtered_history.append(item)
                seen_ips.add(item['ip'])
                if len(filtered_history) >= 10:
                    break
        
        self.history = filtered_history
        self._save_history()
    
    def get_history(self, connection_type: Optional[str] = None) -> List[Dict]:
        """Get connection history
        
        Args:
            connection_type: Filter by connection type (wireless, pairing)
        
        Returns:
            List of history entries
        """
        if connection_type:
            return [h for h in self.history if h.get('type') == connection_type]
        return self.history
    
    def display_history_selection(self, connection_type: Optional[str] = None, 
                                 show_new_option: bool = True) -> Optional[str]:
        """Display history for user selection
        
        Args:
            connection_type: Filter by connection type
            show_new_option: Whether to show "Enter new address" option
        
        Returns:
            Selected address or None if cancelled
        """
        # Show all history for both pairing and wireless since you often
        # pair first then connect, or connect to previously paired devices
        # connection_type parameter kept for API compatibility but not used
        history = self.history  # Always show all history
        
        if not history and not show_new_option:
            return None
        
        # Create selection table
        table = Table(title="Recent Connections", show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("IP Address", style="green")
        table.add_column("Last Used", style="yellow")
        table.add_column("Device", style="magenta")
        
        choices = []
        
        # Add new option first (as 0)
        if show_new_option:
            table.add_row("0", "[bold yellow]Enter new address[/bold yellow]", "", "")
            choices.append("0")
        
        # Add history entries (1-9)
        for i, entry in enumerate(history[:9], 1):
            ip = entry['ip']
            timestamp = datetime.fromisoformat(entry['timestamp'])
            time_str = timestamp.strftime("%Y-%m-%d %H:%M")
            device = entry.get('device_name', 'Unknown')
            
            table.add_row(str(i), ip, time_str, device)
            choices.append(str(i))
        
        console.print(table)
        
        from rich.prompt import Prompt
        choice = Prompt.ask("\nSelect an option", choices=choices)
        
        if choice == "0":
            return "NEW"
        
        # Return the selected IP
        selected_idx = int(choice) - 1
        if 0 <= selected_idx < len(history):
            return history[selected_idx]['ip']
        
        return None
    
    def update_device_name(self, ip: str, device_name: str):
        """Update device name for a given IP address
        
        Args:
            ip: IP address to update
            device_name: Device name/model to set
        """
        for entry in self.history:
            if entry['ip'] == ip:
                entry['device_name'] = device_name
        self._save_history()
    
    def clear_history(self):
        """Clear all connection history"""
        self.history = []
        self._save_history()