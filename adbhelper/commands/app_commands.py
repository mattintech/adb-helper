"""Application management commands for ADB Helper"""
import click
import re
import csv
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from ..core.adb import ADBError
from .utils import DeviceSelector

console = Console()


def register_app_commands(main_group):
    """Register app management commands with the main CLI group"""
    
    @main_group.group(name='app', invoke_without_command=True)
    @click.pass_context
    def app(ctx):
        """Manage Android applications"""
        if ctx.invoked_subcommand is None:
            console.print("\n[bold]App Management Commands:[/bold]\n")
            console.print("  [cyan]adbh app list[/cyan]     - List installed applications")
            console.print("  [cyan]adbh app launch[/cyan]   - Launch an application")
            console.print("  [cyan]adbh app clear[/cyan]    - Clear app data and cache")
            console.print("  [cyan]adbh app stop[/cyan]     - Force stop an application")
            console.print("  [cyan]adbh app info[/cyan]     - Show detailed app information")
            console.print("  [cyan]adbh app backup[/cyan]   - Backup APK file(s) from device")
            console.print("  [cyan]adbh app current[/cyan]  - Show current foreground app\n")
            console.print("Use [cyan]adbh app --help[/cyan] for more information")
    
    @app.command('list')
    @click.option('-d', '--device', help='Target device ID')
    @click.option('-s', '--system', is_flag=True, help='Include system apps')
    @click.option('-f', '--filter', help='Filter apps by name/package')
    @click.option('-3', '--third-party', is_flag=True, help='Show only third-party apps')
    @click.pass_context
    def app_list(ctx, device, system, filter, third_party):
        """List installed applications"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            console.print(f"[yellow]Fetching installed apps from {device_id}...[/yellow]")
            
            # Build the pm list packages command
            cmd = ["pm", "list", "packages"]
            if third_party:
                cmd.append("-3")  # Third-party apps only
            elif not system:
                cmd.append("-3")  # Default to third-party unless system is requested
            
            stdout, stderr, code = device_manager.adb._run_command(["-s", device_id, "shell"] + cmd)
            
            if code != 0:
                console.print(f"[red]Failed to list packages: {stderr}[/red]")
                return
            
            # Parse package list
            packages = []
            for line in stdout.strip().split('\n'):
                if line.startswith('package:'):
                    package_name = line.replace('package:', '')
                    if filter and filter.lower() not in package_name.lower():
                        continue
                    packages.append(package_name)
            
            if not packages:
                console.print("[yellow]No packages found matching criteria[/yellow]")
                return
            
            # Get additional info for each package
            table = Table(title=f"Installed Apps ({len(packages)} found)")
            table.add_column("Package", style="cyan")
            table.add_column("App Name", style="green")
            table.add_column("Version", style="yellow")
            
            # Use cmd package dump to get all app info at once (more efficient)
            console.print("[dim]Getting app details...[/dim]")
            
            # Get detailed package info for all packages at once
            dump_cmd = "cmd package dump | grep -E 'Package \\[|versionName=|applicationLabel='"
            dump_stdout, _, _ = device_manager.adb._run_command(
                ["-s", device_id, "shell", dump_cmd]
            )
            
            # Parse the dump output to build a map of package info
            package_info = {}
            current_package = None
            
            for line in dump_stdout.split('\n'):
                line = line.strip()
                
                # Check for package declaration
                package_match = re.search(r'Package \[(.*?)\]', line)
                if package_match:
                    current_package = package_match.group(1)
                    if current_package not in package_info:
                        package_info[current_package] = {
                            'name': '',
                            'version': 'Unknown'
                        }
                
                # Extract app label
                elif current_package and 'applicationLabel=' in line:
                    label_match = re.search(r'applicationLabel=(.*)', line)
                    if label_match:
                        label = label_match.group(1).strip()
                        if label and label != "null":
                            package_info[current_package]['name'] = label
                
                # Extract version
                elif current_package and 'versionName=' in line:
                    version_match = re.search(r'versionName=([\S]+)', line)
                    if version_match:
                        package_info[current_package]['version'] = version_match.group(1)
            
            # Display the results and build data for export
            app_data = []
            for package in sorted(packages):
                if package in package_info:
                    app_name = package_info[package]['name']
                    version = package_info[package]['version']
                else:
                    # Fallback: get individual package info
                    app_name = package.split('.')[-1].title()
                    version = "Unknown"
                    
                    # Try one more method for this specific package
                    info_stdout, _, _ = device_manager.adb._run_command(
                        ["-s", device_id, "shell", "dumpsys", "package", package, "|", "grep", "-E", "'applicationLabel=|versionName='"]
                    )
                    
                    for line in info_stdout.split('\n'):
                        if 'applicationLabel=' in line:
                            match = re.search(r'applicationLabel=(.*)', line)
                            if match:
                                label = match.group(1).strip()
                                if label and label != "null":
                                    app_name = label
                        elif 'versionName=' in line:
                            match = re.search(r'versionName=([\S]+)', line)
                            if match:
                                version = match.group(1)
                
                table.add_row(package, app_name, version)
                app_data.append({
                    'package': package,
                    'app_name': app_name,
                    'version': version
                })
            
            console.print(table)
            
            # Ask if user wants to export to CSV
            console.print(f"\n[dim]Found {len(app_data)} apps[/dim]")
            if Confirm.ask("\nExport to CSV?", default=False):
                # Generate filename with device info and timestamp
                device_info = device_manager.get_device_info(device_id)
                device_name = device_info.get('model', 'device').replace(' ', '_')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                default_filename = f"apps_{device_name}_{timestamp}.csv"
                filename = Prompt.ask("Save as", default=default_filename)
                
                # Write CSV file
                try:
                    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['package', 'app_name', 'version']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        
                        writer.writeheader()
                        writer.writerows(app_data)
                    
                    console.print(f"[green]✓ Exported to {filename}[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to save CSV: {e}[/red]")
            
        except ADBError as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @app.command('launch')
    @click.argument('package', required=False)
    @click.option('-d', '--device', help='Target device ID')
    @click.option('-a', '--activity', help='Specific activity to launch')
    @click.pass_context
    def app_launch(ctx, package, device, activity):
        """Launch an application"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            if not package:
                # Show list of apps to choose from
                console.print("[yellow]Fetching installed apps...[/yellow]")
                stdout, _, _ = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "pm", "list", "packages", "-3"]
                )
                
                packages = []
                for line in stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        packages.append(line.replace('package:', ''))
                
                if not packages:
                    console.print("[red]No third-party apps found[/red]")
                    return
                
                # Show numbered list
                console.print("\n[bold]Select an app to launch:[/bold]")
                for i, pkg in enumerate(sorted(packages), 1):
                    console.print(f"{i}. {pkg}")
                
                choice = Prompt.ask("\nEnter app number", default="1")
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(packages):
                        package = sorted(packages)[idx]
                    else:
                        console.print("[red]Invalid selection[/red]")
                        return
                except ValueError:
                    console.print("[red]Invalid input[/red]")
                    return
            
            console.print(f"[yellow]Launching {package}...[/yellow]")
            
            if activity:
                # Launch specific activity
                cmd = ["am", "start", f"{package}/{activity}"]
            else:
                # Use monkey to launch the app (finds the main activity)
                cmd = ["monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]
            
            stdout, stderr, code = device_manager.adb._run_command(
                ["-s", device_id, "shell"] + cmd
            )
            
            if code == 0:
                console.print(f"[green]✓ Successfully launched {package}[/green]")
            else:
                console.print(f"[red]Failed to launch app: {stderr or stdout}[/red]")
                
        except ADBError as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @app.command('clear')
    @click.argument('package', required=False)
    @click.option('-d', '--device', help='Target device ID')
    @click.option('-c', '--cache-only', is_flag=True, help='Clear cache only (not data)')
    @click.option('-y', '--yes', is_flag=True, help='Skip confirmation')
    @click.pass_context
    def app_clear(ctx, package, device, cache_only, yes):
        """Clear app data and/or cache"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            if not package:
                # Show list of apps
                console.print("[yellow]Fetching installed apps...[/yellow]")
                stdout, _, _ = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "pm", "list", "packages", "-3"]
                )
                
                packages = []
                for line in stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        packages.append(line.replace('package:', ''))
                
                if not packages:
                    console.print("[red]No third-party apps found[/red]")
                    return
                
                # Show numbered list
                console.print("\n[bold]Select an app to clear:[/bold]")
                for i, pkg in enumerate(sorted(packages), 1):
                    console.print(f"{i}. {pkg}")
                
                choice = Prompt.ask("\nEnter app number", default="1")
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(packages):
                        package = sorted(packages)[idx]
                    else:
                        console.print("[red]Invalid selection[/red]")
                        return
                except ValueError:
                    console.print("[red]Invalid input[/red]")
                    return
            
            # Confirm action
            action = "cache" if cache_only else "data and cache"
            if not yes:
                if not Confirm.ask(f"[yellow]Clear {action} for {package}?[/yellow]", default=False):
                    console.print("[yellow]Cancelled[/yellow]")
                    return
            
            if cache_only:
                # Clear cache only (requires root on newer Android versions)
                console.print(f"[yellow]Clearing cache for {package}...[/yellow]")
                
                # Try using pm clear-cache (might not work on all devices)
                stdout, stderr, code = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "pm", "clear", "--cache-only", package]
                )
                
                if code != 0:
                    # Fallback: try to delete cache directory (requires root)
                    cache_cmd = f"rm -rf /data/data/{package}/cache/*"
                    stdout, stderr, code = device_manager.adb._run_command(
                        ["-s", device_id, "shell", cache_cmd]
                    )
                    
                    if code != 0:
                        console.print("[yellow]Note: Clearing cache may require root access[/yellow]")
                        console.print("Falling back to clearing all app data...")
                        cache_only = False
            
            if not cache_only:
                # Clear all data
                console.print(f"[yellow]Clearing all data for {package}...[/yellow]")
                stdout, stderr, code = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "pm", "clear", package]
                )
            
            if code == 0 and "Success" in stdout:
                console.print(f"[green]✓ Successfully cleared {action} for {package}[/green]")
            else:
                console.print(f"[red]Failed to clear {action}: {stderr or stdout}[/red]")
                
        except ADBError as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @app.command('stop')
    @click.argument('package', required=False)
    @click.option('-d', '--device', help='Target device ID')
    @click.pass_context
    def app_stop(ctx, package, device):
        """Force stop an application"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            if not package:
                # Show running apps
                console.print("[yellow]Fetching running apps...[/yellow]")
                
                # Get list of running apps using ps
                stdout, _, _ = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "ps", "-A"]
                )
                
                # Extract package names from running processes
                running_packages = set()
                for line in stdout.split('\n')[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 9:
                        process_name = parts[-1]
                        # Filter for app packages (usually contain dots)
                        if '.' in process_name and not process_name.startswith('/'):
                            running_packages.add(process_name)
                
                if not running_packages:
                    console.print("[yellow]No running apps found[/yellow]")
                    return
                
                # Show numbered list
                console.print("\n[bold]Select an app to stop:[/bold]")
                packages_list = sorted(list(running_packages))
                for i, pkg in enumerate(packages_list, 1):
                    console.print(f"{i}. {pkg}")
                
                choice = Prompt.ask("\nEnter app number", default="1")
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(packages_list):
                        package = packages_list[idx]
                    else:
                        console.print("[red]Invalid selection[/red]")
                        return
                except ValueError:
                    console.print("[red]Invalid input[/red]")
                    return
            
            console.print(f"[yellow]Force stopping {package}...[/yellow]")
            
            stdout, stderr, code = device_manager.adb._run_command(
                ["-s", device_id, "shell", "am", "force-stop", package]
            )
            
            if code == 0:
                console.print(f"[green]✓ Successfully stopped {package}[/green]")
            else:
                console.print(f"[red]Failed to stop app: {stderr or stdout}[/red]")
                
        except ADBError as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @app.command('backup')
    @click.argument('package', required=False)
    @click.option('-d', '--device', help='Target device ID')
    @click.option('-o', '--output', help='Output directory (default: current directory)')
    @click.option('-a', '--all', 'all_apps', is_flag=True, help='Backup all third-party apps')
    @click.pass_context
    def app_backup(ctx, package, device, output, all_apps):
        """Backup APK file(s) from device"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            import os
            output_dir = output or os.getcwd()
            
            # Ensure output directory exists
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            packages_to_backup = []
            
            if all_apps:
                # Get all third-party apps
                console.print("[yellow]Fetching third-party apps...[/yellow]")
                stdout, _, _ = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "pm", "list", "packages", "-3"]
                )
                
                for line in stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        packages_to_backup.append(line.replace('package:', ''))
                
                if not packages_to_backup:
                    console.print("[red]No third-party apps found[/red]")
                    return
                
                console.print(f"[cyan]Found {len(packages_to_backup)} apps to backup[/cyan]")
            elif package:
                packages_to_backup = [package]
            else:
                # Show list of apps to choose from
                console.print("[yellow]Fetching installed apps...[/yellow]")
                stdout, _, _ = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "pm", "list", "packages", "-3"]
                )
                
                packages = []
                for line in stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        packages.append(line.replace('package:', ''))
                
                if not packages:
                    console.print("[red]No third-party apps found[/red]")
                    return
                
                # Show numbered list
                console.print("\n[bold]Select an app to backup:[/bold]")
                for i, pkg in enumerate(sorted(packages), 1):
                    console.print(f"{i}. {pkg}")
                
                choice = Prompt.ask("\nEnter app number", default="1")
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(packages):
                        packages_to_backup = [sorted(packages)[idx]]
                    else:
                        console.print("[red]Invalid selection[/red]")
                        return
                except ValueError:
                    console.print("[red]Invalid input[/red]")
                    return
            
            # Backup each package
            successful_backups = 0
            failed_backups = []
            
            for pkg in packages_to_backup:
                console.print(f"\n[yellow]Backing up {pkg}...[/yellow]")
                
                # Get APK path on device
                path_stdout, _, path_code = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "pm", "path", pkg]
                )
                
                if path_code != 0 or not path_stdout.strip():
                    console.print(f"[red]Failed to find APK path for {pkg}[/red]")
                    failed_backups.append(pkg)
                    continue
                
                # Extract base APK path (first line, remove "package:" prefix)
                apk_path = path_stdout.strip().split('\n')[0].replace('package:', '')
                
                # Get version info for filename
                version = "unknown"
                info_stdout, _, _ = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "dumpsys", "package", pkg, "|", "grep", "versionName="]
                )
                
                version_match = re.search(r'versionName=([\S]+)', info_stdout)
                if version_match:
                    version = version_match.group(1)
                    # Clean version string for filename
                    version = re.sub(r'[^\w.-]', '_', version)
                
                # Create filename
                apk_filename = f"{pkg}_{version}.apk"
                output_path = os.path.join(output_dir, apk_filename)
                
                # Pull APK from device
                console.print(f"[dim]Pulling from {apk_path}...[/dim]")
                pull_stdout, pull_stderr, pull_code = device_manager.adb._run_command(
                    ["-s", device_id, "pull", apk_path, output_path]
                )
                
                if pull_code == 0:
                    # Get file size
                    file_size = os.path.getsize(output_path)
                    size_mb = file_size / (1024 * 1024)
                    console.print(f"[green]✓ Saved to {output_path} ({size_mb:.1f} MB)[/green]")
                    successful_backups += 1
                else:
                    console.print(f"[red]Failed to pull APK: {pull_stderr or pull_stdout}[/red]")
                    failed_backups.append(pkg)
                    # Clean up partial file if it exists
                    if os.path.exists(output_path):
                        os.remove(output_path)
            
            # Summary
            console.print(f"\n[bold]Backup Summary:[/bold]")
            console.print(f"[green]Successful: {successful_backups}[/green]")
            if failed_backups:
                console.print(f"[red]Failed: {len(failed_backups)}[/red]")
                for pkg in failed_backups:
                    console.print(f"  • {pkg}")
                    
        except ADBError as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @app.command('current')
    @click.option('-d', '--device', help='Target device ID')
    @click.option('-w', '--watch', is_flag=True, help='Watch for app changes')
    @click.option('-i', '--interval', default=1, help='Watch interval in seconds')
    @click.pass_context
    def app_current(ctx, device, watch, interval):
        """Show the current foreground app"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            def get_current_app():
                """Get current foreground app using multiple methods for compatibility"""
                
                # Method 1: Try using dumpsys window (works on most Android versions)
                stdout, _, code = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "dumpsys", "window", "windows", "|", "grep", "-E", "'mCurrentFocus|mFocusedApp'"]
                )
                
                if code == 0 and stdout:
                    # Parse mCurrentFocus or mFocusedApp
                    for line in stdout.split('\n'):
                        if 'mCurrentFocus=' in line or 'mFocusedApp=' in line:
                            # Extract package/activity from lines like:
                            # mCurrentFocus=Window{... com.example.app/com.example.app.MainActivity}
                            match = re.search(r'(\w+\.[\w\.]+)/(\w+\.[\w\.]+)', line)
                            if match:
                                return match.group(1), match.group(2)
                            # Sometimes it's just the package
                            match = re.search(r'(\w+\.[\w\.]+)}', line)
                            if match:
                                return match.group(1), None
                
                # Method 2: Try using dumpsys activity (for older Android versions)
                stdout, _, code = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "dumpsys", "activity", "recents", "|", "grep", "'Recent #0'", "-A", "1"]
                )
                
                if code == 0 and stdout:
                    match = re.search(r'(\w+\.[\w\.]+)/(\w+\.[\w\.]+)', stdout)
                    if match:
                        return match.group(1), match.group(2)
                
                # Method 3: Try using dumpsys window displays (newer Android)
                stdout, _, code = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "dumpsys", "window", "displays", "|", "grep", "'mCurrentFocus'"]
                )
                
                if code == 0 and stdout:
                    match = re.search(r'(\w+\.[\w\.]+)/(\w+\.[\w\.]+)', stdout)
                    if match:
                        return match.group(1), match.group(2)
                
                # Method 4: Try using dumpsys activity activities (most reliable fallback)
                stdout, _, code = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "dumpsys", "activity", "activities", "|", "grep", "mResumedActivity"]
                )
                
                if code == 0 and stdout:
                    match = re.search(r'(\w+\.[\w\.]+)/(\w+\.[\w\.]+)', stdout)
                    if match:
                        return match.group(1), match.group(2)
                
                return None, None
            
            def get_app_name(package):
                """Get the friendly app name for a package"""
                if not package:
                    return "Unknown"
                
                # Try to get app label
                stdout, _, _ = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "dumpsys", "package", package, "|", "grep", "applicationLabel="]
                )
                
                if stdout:
                    match = re.search(r'applicationLabel=(.*)', stdout)
                    if match:
                        label = match.group(1).strip()
                        if label and label != "null":
                            return label
                
                # Fallback to package name
                return package
            
            if watch:
                console.print(f"[yellow]Watching for app changes (interval: {interval}s, press Ctrl+C to stop)...[/yellow]\n")
                
                last_package = None
                import time
                
                try:
                    while True:
                        package, activity = get_current_app()
                        
                        if package != last_package:
                            if package:
                                app_name = get_app_name(package)
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                
                                console.print(f"[dim]{timestamp}[/dim] [bold green]{app_name}[/bold green]")
                                console.print(f"  Package:  [cyan]{package}[/cyan]")
                                if activity:
                                    console.print(f"  Activity: [yellow]{activity}[/yellow]")
                                console.print()
                                
                                last_package = package
                            else:
                                if last_package is not None:
                                    timestamp = datetime.now().strftime("%H:%M:%S")
                                    console.print(f"[dim]{timestamp}[/dim] [red]No app in foreground[/red]\n")
                                    last_package = None
                        
                        time.sleep(interval)
                        
                except KeyboardInterrupt:
                    console.print("\n[yellow]Stopped watching[/yellow]")
            else:
                # One-time check
                package, activity = get_current_app()
                
                if package:
                    app_name = get_app_name(package)
                    
                    console.print(f"\n[bold]Current Foreground App[/bold]")
                    console.print(f"App Name:  [bold green]{app_name}[/bold green]")
                    console.print(f"Package:   [cyan]{package}[/cyan]")
                    if activity:
                        console.print(f"Activity:  [yellow]{activity}[/yellow]")
                    
                    # Get additional info
                    info_stdout, _, _ = device_manager.adb._run_command(
                        ["-s", device_id, "shell", "dumpsys", "package", package, "|", "grep", "versionName="]
                    )
                    
                    if info_stdout:
                        version_match = re.search(r'versionName=([\S]+)', info_stdout)
                        if version_match:
                            console.print(f"Version:   [magenta]{version_match.group(1)}[/magenta]")
                else:
                    console.print("[red]Could not determine current foreground app[/red]")
                    console.print("[dim]The device may be on the home screen or locked[/dim]")
                    
        except ADBError as e:
            console.print(f"[red]Error: {e}[/red]")
    
    @app.command('info')
    @click.argument('package', required=False)
    @click.option('-d', '--device', help='Target device ID')
    @click.pass_context
    def app_info(ctx, package, device):
        """Show detailed app information"""
        device_manager = ctx.obj['device_manager']
        
        try:
            device_id = DeviceSelector.select_single_device(device_manager, device)
            if not device_id:
                return
            
            if not package:
                # Show list of apps
                console.print("[yellow]Fetching installed apps...[/yellow]")
                stdout, _, _ = device_manager.adb._run_command(
                    ["-s", device_id, "shell", "pm", "list", "packages", "-3"]
                )
                
                packages = []
                for line in stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        packages.append(line.replace('package:', ''))
                
                if not packages:
                    console.print("[red]No third-party apps found[/red]")
                    return
                
                # Show numbered list
                console.print("\n[bold]Select an app to inspect:[/bold]")
                for i, pkg in enumerate(sorted(packages), 1):
                    console.print(f"{i}. {pkg}")
                
                choice = Prompt.ask("\nEnter app number", default="1")
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(packages):
                        package = sorted(packages)[idx]
                    else:
                        console.print("[red]Invalid selection[/red]")
                        return
                except ValueError:
                    console.print("[red]Invalid input[/red]")
                    return
            
            console.print(f"\n[bold]App Information for {package}[/bold]\n")
            
            # Get package info
            stdout, _, _ = device_manager.adb._run_command(
                ["-s", device_id, "shell", "dumpsys", "package", package]
            )
            
            # Parse relevant information
            info = {
                "Version": "Unknown",
                "Version Code": "Unknown",
                "Install Time": "Unknown",
                "Update Time": "Unknown",
                "Data Dir": "Unknown",
                "APK Path": "Unknown",
                "Permissions": []
            }
            
            # Extract information
            in_permissions = False
            for line in stdout.split('\n'):
                line = line.strip()
                
                if 'versionName=' in line:
                    match = re.search(r'versionName=([\S]+)', line)
                    if match:
                        info["Version"] = match.group(1)
                
                if 'versionCode=' in line:
                    match = re.search(r'versionCode=(\d+)', line)
                    if match:
                        info["Version Code"] = match.group(1)
                
                if 'firstInstallTime=' in line:
                    match = re.search(r'firstInstallTime=(.*)', line)
                    if match:
                        info["Install Time"] = match.group(1)
                
                if 'lastUpdateTime=' in line:
                    match = re.search(r'lastUpdateTime=(.*)', line)
                    if match:
                        info["Update Time"] = match.group(1)
                
                if 'dataDir=' in line:
                    match = re.search(r'dataDir=(.*)', line)
                    if match:
                        info["Data Dir"] = match.group(1)
                
                if 'codePath=' in line:
                    match = re.search(r'codePath=(.*)', line)
                    if match:
                        info["APK Path"] = match.group(1)
                
                # Parse permissions
                if 'grantedPermissions:' in line or 'requested permissions:' in line:
                    in_permissions = True
                elif in_permissions and line and not line.startswith(' '):
                    in_permissions = False
                elif in_permissions and line:
                    perm = line.strip()
                    if perm.startswith('android.permission.'):
                        perm = perm.replace('android.permission.', '')
                    info["Permissions"].append(perm)
            
            # Get app size
            size_stdout, _, _ = device_manager.adb._run_command(
                ["-s", device_id, "shell", "du", "-sh", f"/data/data/{package}", "2>/dev/null"]
            )
            if size_stdout.strip():
                size = size_stdout.split()[0]
                info["Data Size"] = size
            
            # Display information
            for key, value in info.items():
                if key == "Permissions":
                    if value:
                        console.print(f"[cyan]{key}:[/cyan]")
                        for perm in sorted(set(value)):
                            console.print(f"  • {perm}")
                else:
                    console.print(f"[cyan]{key}:[/cyan] {value}")
            
            # Check if app is currently running
            ps_stdout, _, _ = device_manager.adb._run_command(
                ["-s", device_id, "shell", "pidof", package]
            )
            if ps_stdout.strip():
                console.print(f"\n[green]Status: Running (PID: {ps_stdout.strip()})[/green]")
            else:
                console.print("\n[yellow]Status: Not running[/yellow]")
                
        except ADBError as e:
            console.print(f"[red]Error: {e}[/red]")