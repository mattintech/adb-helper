"""SPAKE2-based pairing implementation (experimental)"""

import socket
import ssl
import threading
import time
from typing import Optional, Tuple
from spake2 import SPAKE2_A, SPAKE2_B
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta, timezone
from rich.console import Console

console = Console()

class SPAKE2PairingServer:
    """Experimental SPAKE2 pairing server for ADB"""
    
    def __init__(self, session_name: str, pairing_code: str, port: int = 0):
        self.session_name = session_name
        self.pairing_code = pairing_code.encode('utf-8')
        self.port = port or self._find_free_port()
        self.server_thread = None
        self.running = False
        self.paired_devices = []
        
        # Generate self-signed certificate for TLS
        self.cert_path, self.key_path = self._generate_certificate()
        
    def _find_free_port(self) -> int:
        """Find a free port for the pairing service"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def _generate_certificate(self) -> Tuple[str, str]:
        """Generate a self-signed certificate for TLS"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "ADBHelper"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ADBHelper"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("*.local"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256(), backend=default_backend())
        
        # Save to temporary files
        import tempfile
        cert_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pem')
        cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
        cert_file.close()
        
        key_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.key')
        key_file.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
        key_file.close()
        
        return cert_file.name, key_file.name
    
    def start(self) -> bool:
        """Start the SPAKE2 pairing server"""
        try:
            self.running = True
            self.server_thread = threading.Thread(target=self._run_server)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            console.print(f"[green]✓ SPAKE2 pairing server started on port {self.port}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to start SPAKE2 server: {e}[/red]")
            return False
    
    def _run_server(self):
        """Run the pairing server"""
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.cert_path, self.key_path)
        
        # Create socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', self.port))
        server_socket.listen(1)
        server_socket.settimeout(1.0)
        
        # Wrap with SSL
        # Note: Android might not accept self-signed certs without proper setup
        
        while self.running:
            try:
                client_socket, address = server_socket.accept()
                console.print(f"\n[yellow]Device connecting from {address[0]}:{address[1]}...[/yellow]")
                
                # Handle connection in a separate thread
                handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                handler.daemon = True
                handler.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    console.print(f"[red]Server error: {e}[/red]")
        
        server_socket.close()
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """Handle a client connection with SPAKE2"""
        try:
            # For now, implement basic SPAKE2 without full ADB protocol
            # In reality, we'd need to handle A_STLS, CNXN commands, etc.
            
            # Initialize SPAKE2 on server side (B)
            spake_b = SPAKE2_B(self.pairing_code)
            
            # Generate and send our message
            msg_b = spake_b.start()
            client_socket.send(len(msg_b).to_bytes(4, 'big'))
            client_socket.send(msg_b)
            
            console.print("[dim]Sent SPAKE2 message to device[/dim]")
            
            # Receive client's message
            msg_len = int.from_bytes(client_socket.recv(4), 'big')
            msg_a = client_socket.recv(msg_len)
            
            console.print("[dim]Received SPAKE2 message from device[/dim]")
            
            # Complete the handshake
            key_b = spake_b.finish(msg_a)
            
            if key_b:
                console.print(f"[green]✓ SPAKE2 handshake completed![/green]")
                console.print(f"[dim]Shared key established: {key_b.hex()[:16]}...[/dim]")
                
                # In a real implementation, we'd continue with ADB protocol
                # For now, just acknowledge success
                client_socket.send(b"PAIRED_OK")
                
                self.paired_devices.append(address[0])
            else:
                console.print("[red]✗ SPAKE2 handshake failed![/red]")
                client_socket.send(b"PAIRED_FAIL")
            
        except Exception as e:
            console.print(f"[red]Error handling client: {e}[/red]")
        finally:
            client_socket.close()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_thread:
            self.server_thread.join(timeout=2)
        
        # Clean up certificate files
        import os
        try:
            os.unlink(self.cert_path)
            os.unlink(self.key_path)
        except:
            pass
    
    def wait_for_pairing(self, timeout: int = 120) -> Optional[str]:
        """Wait for a device to pair"""
        start_time = time.time()
        
        try:
            while self.running and (time.time() - start_time) < timeout:
                if self.paired_devices:
                    return self.paired_devices[0]
                time.sleep(0.5)
                
            return None
            
        except KeyboardInterrupt:
            return None