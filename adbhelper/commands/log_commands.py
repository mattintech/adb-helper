"""Log command registration"""
import os
import subprocess
import platform
import sys
import re
import threading
import queue
from datetime import datetime
from typing import List, Dict
import click
from rich.console import Console
from rich.text import Text
from .utils import DeviceSelector

console = Console()

# Color palette for different devices
DEVICE_COLORS = [
    "bright_blue",
    "bright_green", 
    "bright_yellow",
    "bright_magenta",
    "bright_cyan",
    "bright_red",
    "blue",
    "green",
    "yellow",
    "magenta",
    "cyan",
    "red"
]


def register_log_commands(main_group):
    """Register log commands with the main CLI group"""
    
    @main_group.group(name='log', invoke_without_command=True)
    @click.pass_context
    def log(ctx):
        """View and manage device logs (logcat)"""
        if ctx.invoked_subcommand is None:
            console.print("\n[bold]Log Options:[/bold]\n")
            console.print("  [cyan]adbh log view[/cyan]    - View live device logs (supports multiple devices with color coding)")
            console.print("  [cyan]adbh log dump[/cyan]    - Dump current logs and exit")
            console.print("  [cyan]adbh log clear[/cyan]   - Clear device logs\n")
            console.print("Use [cyan]adbh log --help[/cyan] for more information")
    
    @log.command('view')
    @click.option('-f', '--filter', multiple=True, help='Filter log output (can be used multiple times)')
    @click.option('-s', '--save', is_flag=True, help='Save log output to file')
    @click.option('--device', help='Target device ID (skip all selection prompts)')
    @click.option('--separate', is_flag=True, help='Open separate windows for each device (old behavior)')
    @click.pass_context
    def log_view(ctx, filter, save, device, separate):
        """View live device logs (single or multiple devices with color coding)"""
        device_manager = ctx.obj['device_manager']
        
        try:
            target_devices = DeviceSelector.select_multiple_devices(device_manager, device)
            if not target_devices:
                return
            
            # Single device mode
            if len(target_devices) == 1:
                device_id = target_devices[0]
                
                # Build logcat command
                logcat_args = ["-s", device_id, "logcat"]
                
                # Setup file saving if requested
                log_file = None
                if save:
                    log_file = _setup_log_file(device_id)
                
                # Live mode
                console.print(f"[yellow]Starting live log view...[/yellow]")
                console.print("[dim]Press Ctrl+C to stop[/dim]\n")
                
                try:
                    # Start logcat process
                    process = subprocess.Popen(
                        [device_manager.adb.adb_path] + logcat_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        errors='replace',  # Replace invalid UTF-8 characters
                        bufsize=1
                    )
                    
                    # Process output line by line
                    for line in process.stdout:
                        # Apply filter if any
                        if filter:
                            if not _should_include_line(line, filter):
                                continue
                        
                        # Output to console and file
                        console.print(line.rstrip())
                        if log_file:
                            log_file.write(line)
                            log_file.flush()  # Ensure it's written immediately
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Log viewing stopped[/yellow]")
                    process.terminate()
                finally:
                    if log_file:
                        log_file.close()
                        
                return
            
            # Multi-device mode
            if separate:
                # Old behavior - separate terminal windows
                console.print(f"[green]Launching logs for {len(target_devices)} device(s) in separate windows...[/green]")
                
                for device_id in target_devices:
                    # Launch new terminal window for each device
                    cmd_args = [sys.executable, "-m", "adbhelper.cli", "log", "view", "--device", device_id]
                    
                    if save:
                        cmd_args.append("--save")
                    for f in filter:
                        cmd_args.extend(["--filter", f])
                    
                    if platform.system() == "Darwin":  # macOS
                        terminal_cmd = [
                            "osascript", "-e",
                            f'tell app "Terminal" to do script "{" ".join(cmd_args)}"'
                        ]
                    elif platform.system() == "Linux":
                        terminal_cmd = ["gnome-terminal", "--", *cmd_args]
                    elif platform.system() == "Windows":
                        terminal_cmd = ["cmd", "/c", "start", "cmd", "/k", *cmd_args]
                    else:
                        console.print("[red]Multi-device mode not supported on this platform[/red]")
                        return
                    
                    subprocess.Popen(terminal_cmd)
            else:
                # New behavior - unified color-coded view
                _view_multi_device_logs(device_manager, target_devices, filter, save)
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @log.command('dump')
    @click.option('-f', '--filter', multiple=True, help='Filter log output (can be used multiple times)')
    @click.option('-s', '--save', is_flag=True, help='Save log output to file')
    @click.option('--device', help='Target device ID (skip all selection prompts)')
    @click.pass_context
    def log_dump(ctx, filter, save, device):
        """Dump current device logs and exit"""
        device_manager = ctx.obj['device_manager']
        
        try:
            target_devices = DeviceSelector.select_multiple_devices(device_manager, device)
            if not target_devices:
                return
            
            # Process each device
            for device_id in target_devices:
                if len(target_devices) > 1:
                    console.print(f"\n[bold]Device: {device_id}[/bold]")
                
                # Setup file saving if requested
                log_file = None
                if save:
                    log_file = _setup_log_file(device_id, dump=True)
                
                # Dump mode - get all at once
                console.print("[yellow]Dumping current log...[/yellow]")
                process = subprocess.run(
                    [device_manager.adb.adb_path, "-s", device_id, "logcat", "-d"],
                    capture_output=True,
                    universal_newlines=True,
                    errors='replace'  # Replace invalid UTF-8 characters
                )
                
                output = process.stdout
                
                # Apply filters if any
                if filter and output:
                    lines = output.split('\n')
                    filtered_lines = [line for line in lines if _should_include_line(line, filter)]
                    output = '\n'.join(filtered_lines)
                
                # Output to console and/or file
                if output:
                    if not save:  # Only print to console if not saving
                        console.print(output)
                    if log_file:
                        log_file.write(output)
                        log_file.close()
                        console.print(f"[green]✓ Log dump complete[/green]")
                else:
                    console.print("[yellow]No log entries found[/yellow]")
                    if log_file:
                        log_file.close()
                        
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @log.command('clear')
    @click.option('--device', help='Target device ID (skip all selection prompts)')
    @click.pass_context
    def log_clear(ctx, device):
        """Clear device logs"""
        device_manager = ctx.obj['device_manager']
        
        try:
            target_devices = DeviceSelector.select_multiple_devices(device_manager, device)
            if not target_devices:
                return
            
            # Clear logs for each device
            for device_id in target_devices:
                console.print(f"[yellow]Clearing log for {device_id}...[/yellow]")
                device_manager.adb._run_command(["-s", device_id, "logcat", "-c"])
                console.print(f"[green]✓ Log cleared for {device_id}[/green]")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    


def _setup_log_file(device_id: str, dump: bool = False) -> object:
    """Setup log file for saving output"""
    # Create logs directory
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create filename with timestamp and device ID
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    # Sanitize device ID for filename
    safe_device_id = device_id.replace(":", "-").replace(".", "_")
    suffix = "_dump" if dump else ""
    filename = f"logcat_{safe_device_id}_{timestamp}{suffix}.log"
    filepath = os.path.join(logs_dir, filename)
    
    log_file = open(filepath, 'w')
    console.print(f"[green]✓ Saving log to: {filepath}[/green]")
    return log_file


def _should_include_line(line: str, filters: tuple) -> bool:
    """Check if a line should be included based on filters"""
    if not filters:
        return True
    
    if len(filters) == 1:
        return filters[0] in line
    else:
        pattern = re.compile('|'.join(f"({re.escape(f)})" for f in filters))
        return bool(pattern.search(line))


def _view_multi_device_logs(device_manager, target_devices: List[str], filter: tuple, save: bool):
    """View logs from multiple devices in a unified color-coded display"""
    # Get device information
    devices = device_manager.list_devices()
    
    # Assign colors to devices
    device_colors = {}
    device_names = {}
    for i, device_id in enumerate(target_devices):
        device_colors[device_id] = DEVICE_COLORS[i % len(DEVICE_COLORS)]
        # Get device model for better identification
        device_info = next((d for d in devices if d['id'] == device_id), {})
        device_names[device_id] = device_info.get('model', device_id.split(':')[0] if ':' in device_id else device_id[:8])
    
    # Show device color assignments
    console.print("\n[bold]Device color assignments:[/bold]")
    for device_id, color in device_colors.items():
        name = device_names[device_id]
        console.print(f"  [{color}]● {name}[/{color}] ({device_id})")
    
    # Setup log file if requested
    log_file = None
    if save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logcat_multi_{timestamp}.log"
        filepath = os.path.join(os.getcwd(), "logs", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        log_file = open(filepath, 'w')
        console.print(f"\n[green]✓ Saving combined log to: {filepath}[/green]")
    
    console.print("\n[yellow]Starting multi-device log view...[/yellow]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    # Create queues and threads for each device
    log_queue = queue.Queue()
    threads = []
    processes = []
    
    def read_device_logs(device_id, color, name):
        """Read logs from a device and put them in the queue"""
        try:
            process = subprocess.Popen(
                [device_manager.adb.adb_path, "-s", device_id, "logcat"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                errors='replace',  # Replace invalid UTF-8 characters
                bufsize=1
            )
            processes.append(process)
            
            for line in process.stdout:
                if line.strip():
                    log_queue.put((device_id, color, name, line.rstrip()))
                    
        except Exception as e:
            log_queue.put((device_id, color, name, f"[ERROR] {str(e)}"))
    
    # Start threads for each device
    for device_id in target_devices:
        thread = threading.Thread(
            target=read_device_logs,
            args=(device_id, device_colors[device_id], device_names[device_id]),
            daemon=True
        )
        thread.start()
        threads.append(thread)
    
    # Main loop to display logs
    try:
        while True:
            try:
                device_id, color, name, line = log_queue.get(timeout=0.1)
                
                # Apply filters if any
                if filter and not _should_include_line(line, filter):
                    continue
                
                # Create formatted output with device identifier
                text = Text()
                text.append(f"[{name}] ", style=f"bold {color}")
                text.append(line)
                
                console.print(text)
                
                # Save to file if requested
                if log_file:
                    log_file.write(f"[{device_id}] {line}\n")
                    log_file.flush()
                    
            except queue.Empty:
                continue
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping multi-device log view...[/yellow]")
        
        # Terminate all processes
        for process in processes:
            if process.poll() is None:
                process.terminate()
                
        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=1)
            
    finally:
        if log_file:
            log_file.close()
            console.print("[green]✓ Log file saved[/green]")