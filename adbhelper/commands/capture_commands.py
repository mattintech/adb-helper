"""Capture command registration"""
import os
import time
import subprocess
import re
import platform
import webbrowser
from datetime import datetime
import click
from rich.console import Console
from .utils import DeviceSelector

console = Console()


def register_capture_commands(main_group):
    """Register capture commands with the main CLI group"""
    
    @main_group.group(name='capture', invoke_without_command=True)
    @click.pass_context
    def capture(ctx):
        """Capture screenshots and recordings from device"""
        if ctx.invoked_subcommand is None:
            console.print("\n[bold]Capture Options:[/bold]\n")
            console.print("  [cyan]adbh capture screenshot[/cyan] - Take a screenshot")
            console.print("  [cyan]adbh capture record[/cyan]    - Record screen (video)\n")
            console.print("Use [cyan]adbh capture --help[/cyan] for more information")
    
    @capture.command('screenshot')
    @click.option('-o', '--open', 'open_file', is_flag=True, help='Open screenshot after capture')
    @click.option('-d', '--device', help='Target device ID')
    @click.pass_context
    def screenshot(ctx, open_file, device):
        """Take a screenshot from the device"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            # Wake up the device
            console.print("[yellow]Waking up device...[/yellow]")
            device_manager.adb._run_command(["-s", device_id, "shell", "input", "keyevent", "KEYCODE_WAKEUP"])
            
            # Small delay to ensure screen is on
            time.sleep(0.5)
            
            # Create screenshots directory
            screenshots_dir = os.path.join(os.getcwd(), "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Get current time
            now = datetime.now()
            time_str = now.strftime("%H:%M")
            
            # Count existing screenshots for this minute
            existing_files = [f for f in os.listdir(screenshots_dir) if f.startswith(time_str)]
            screenshot_num = len(existing_files) + 1
            
            # Try to get foreground app name
            app_name = ""
            try:
                stdout, _, _ = device_manager.adb._run_command([
                    "-s", device_id, "shell", 
                    "dumpsys", "window", "windows", "|", "grep", "-E", "'mCurrentFocus|mFocusedApp'"
                ])
                
                # Extract app name from output
                match = re.search(r'[^/]+/([^}\s]+)', stdout)
                if match:
                    app_name = f"-{match.group(1).split('.')[-1]}"
            except:
                pass
            
            # Create filename
            filename = f"{time_str}-{screenshot_num}{app_name}.png"
            filepath = os.path.join(screenshots_dir, filename)
            
            # Take screenshot directly to file
            console.print(f"[yellow]Taking screenshot...[/yellow]")
            process = subprocess.run([
                device_manager.adb.adb_path, "-s", device_id, "exec-out", "screencap", "-p"
            ], capture_output=True)
            
            if process.returncode == 0:
                with open(filepath, 'wb') as f:
                    f.write(process.stdout)
                console.print(f"[green]✓ Screenshot saved to: {filepath}[/green]")
                
                # Open the file if requested
                if open_file:
                    # Use webbrowser which handles cross-platform opening
                    webbrowser.open(f'file://{os.path.abspath(filepath)}')
                    console.print(f"[green]✓ Opening screenshot...[/green]")
            else:
                console.print(f"[red]Failed to capture screenshot: {process.stderr.decode()}[/red]")
                    
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @capture.command('record')
    @click.option('-t', '--time', default=180, help='Recording duration in seconds (default: 180)')
    @click.option('-d', '--device', help='Target device ID')
    @click.pass_context
    def record(ctx, time, device):
        """Record screen video from the device"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            # Wake up the device
            console.print("[yellow]Waking up device...[/yellow]")
            device_manager.adb._run_command(["-s", device_id, "shell", "input", "keyevent", "KEYCODE_WAKEUP"])
            
            # Create recordings directory
            recordings_dir = os.path.join(os.getcwd(), "recordings")
            os.makedirs(recordings_dir, exist_ok=True)
            
            # Create filename with timestamp
            now = datetime.now()
            filename = now.strftime("recording_%Y%m%d_%H%M%S.mp4")
            filepath = os.path.join(recordings_dir, filename)
            
            # Temporary file on device
            temp_file = f"/sdcard/{filename}"
            
            console.print(f"[yellow]Recording for {time} seconds...[/yellow]")
            console.print("[dim]Press Ctrl+C to stop early[/dim]")
            
            try:
                # Start recording
                process = device_manager.adb._run_command_async([
                    "-s", device_id, "shell", "screenrecord", 
                    "--time-limit", str(time), temp_file
                ])
                
                # Wait for recording to complete or user interrupt
                process.wait()
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping recording...[/yellow]")
                # Kill the screenrecord process
                device_manager.adb._run_command(["-s", device_id, "shell", "pkill", "-2", "screenrecord"])
                time.sleep(1)  # Give it time to save
            
            # Pull the file from device
            console.print("[yellow]Downloading recording...[/yellow]")
            _, stderr, code = device_manager.adb._run_command([
                "-s", device_id, "pull", temp_file, filepath
            ])
            
            if code == 0:
                console.print(f"[green]✓ Recording saved to: {filepath}[/green]")
                
                # Clean up temp file on device
                device_manager.adb._run_command(["-s", device_id, "shell", "rm", temp_file])
            else:
                console.print(f"[red]Failed to download recording: {stderr}[/red]")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")