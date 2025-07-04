"""Log command registration"""
import os
import subprocess
import platform
import sys
import re
from datetime import datetime
import click
from rich.console import Console
from .utils import DeviceSelector

console = Console()


def register_log_commands(main_group):
    """Register log commands with the main CLI group"""
    
    @main_group.group(name='log', invoke_without_command=True)
    @click.pass_context
    def log(ctx):
        """View and manage device logs (logcat)"""
        if ctx.invoked_subcommand is None:
            console.print("\n[bold]Log Options:[/bold]\n")
            console.print("  [cyan]adbh log view[/cyan]    - View live device logs")
            console.print("  [cyan]adbh log dump[/cyan]    - Dump current logs and exit")
            console.print("  [cyan]adbh log clear[/cyan]   - Clear device logs\n")
            console.print("Use [cyan]adbh log --help[/cyan] for more information")
    
    @log.command('view')
    @click.option('-f', '--filter', multiple=True, help='Filter log output (can be used multiple times)')
    @click.option('-s', '--save', is_flag=True, help='Save log output to file')
    @click.option('--device', help='Target device ID (skip all selection prompts)')
    @click.pass_context
    def log_view(ctx, filter, save, device):
        """View live device logs"""
        device_manager = ctx.obj['device_manager']
        
        try:
            target_devices = DeviceSelector.select_multiple_devices(device_manager, device)
            if not target_devices:
                return
            
            # Handle multi-device mode
            if len(target_devices) > 1:
                console.print(f"[green]Launching logs for {len(target_devices)} device(s)...[/green]")
                
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
                
                return
            
            # Single device mode
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
                    text=True,
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
                    text=True
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