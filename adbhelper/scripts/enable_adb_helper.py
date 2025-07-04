#!/usr/bin/env python3
"""Helper script to guide users through enabling ADB debugging"""

import time
import subprocess
import os
from rich.console import Console
from rich.prompt import Prompt

console = Console()

def check_adb_status():
    """Check if ADB can see any devices"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        devices = [line for line in lines if line.strip()]
        return len(devices) > 0, devices
    except FileNotFoundError:
        return False, ["ADB not installed"]

def guide_usb_debugging():
    """Guide for enabling USB debugging"""
    console.print("\n[bold cyan]USB Debugging Setup[/bold cyan]\n")
    
    steps = [
        ("Connect your Android device via USB cable", "Press Enter when connected..."),
        ("Unlock your device", "Press Enter when unlocked..."),
        ("Open Settings app", "Press Enter when in Settings..."),
        ("Scroll down and tap 'About phone'", "Press Enter when in About phone..."),
        ("Find 'Build number' and tap it 7 times", "You should see 'You are now a developer!'"),
        ("Go back to main Settings", "Press Enter when back in Settings..."),
        ("Find and tap 'System' (might be under Advanced)", "Press Enter..."),
        ("Tap 'Developer options'", "Press Enter when in Developer options..."),
        ("Enable 'USB debugging' toggle", "Press Enter when enabled..."),
        ("A dialog will appear on your phone - tap 'Allow'", "Also check 'Always allow from this computer'"),
    ]
    
    for i, (instruction, prompt) in enumerate(steps, 1):
        console.print(f"\n[yellow]Step {i}/{len(steps)}:[/yellow] {instruction}")
        input(f"    → {prompt}")
        
        # Check if ADB is working after critical steps
        if i >= 9:
            connected, devices = check_adb_status()
            if connected:
                console.print("\n[green]✓ Success! USB debugging is now enabled![/green]")
                console.print(f"  Devices: {devices}")
                return True
    
    return False

def guide_wireless_debugging():
    """Guide for enabling Wireless debugging (Android 11+)"""
    console.print("\n[bold cyan]Wireless Debugging Setup (Android 11+)[/bold cyan]\n")
    
    console.print("[yellow]Note:[/yellow] Wireless debugging requires Android 11 or later\n")
    
    steps = [
        ("Make sure your phone and computer are on the same WiFi network", "Press Enter when ready..."),
        ("Open Settings app on your phone", "Press Enter when in Settings..."),
        ("Scroll down and tap 'About phone'", "Press Enter when in About phone..."),
        ("Find 'Build number' and tap it 7 times", "You should see 'You are now a developer!'"),
        ("Go back to main Settings", "Press Enter when back in Settings..."),
        ("Find and tap 'System' (might be under Advanced)", "Press Enter..."),
        ("Tap 'Developer options'", "Press Enter when in Developer options..."),
        ("Find and enable 'Wireless debugging'", "Press Enter when enabled..."),
        ("Tap on 'Wireless debugging' to enter its settings", "Press Enter when in Wireless debugging..."),
        ("Tap 'Pair device with pairing code'", "You'll see an IP address, port, and pairing code"),
    ]
    
    for i, (instruction, prompt) in enumerate(steps, 1):
        console.print(f"\n[yellow]Step {i}/{len(steps)}:[/yellow] {instruction}")
        input(f"    → {prompt}")
    
    console.print("\n[bold]Now on your computer:[/bold]")
    
    # Get pairing info from user
    ip_port = Prompt.ask("\nEnter the IP address and port shown on your phone (e.g., 192.168.1.100:37251)")
    pairing_code = Prompt.ask("Enter the pairing code")
    
    # Try to pair
    console.print(f"\n[yellow]Attempting to pair with {ip_port}...[/yellow]")
    try:
        result = subprocess.run(
            ['adb', 'pair', ip_port, pairing_code],
            capture_output=True,
            text=True,
            input=pairing_code + '\n',
            timeout=30
        )
        
        if "Successfully paired" in result.stdout:
            console.print("[green]✓ Successfully paired![/green]")
            
            # Now connect
            console.print("\n[yellow]Go back to Wireless debugging settings on your phone[/yellow]")
            connect_ip = Prompt.ask("Enter the IP address and port shown under 'IP address & Port' (e.g., 192.168.1.100:37259)")
            
            result = subprocess.run(['adb', 'connect', connect_ip], capture_output=True, text=True)
            
            if "connected" in result.stdout:
                console.print(f"[green]✓ Successfully connected to {connect_ip}![/green]")
                return True
            else:
                console.print(f"[red]Failed to connect: {result.stderr}[/red]")
        else:
            console.print(f"[red]Failed to pair: {result.stdout} {result.stderr}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    
    return False

def main():
    """Main entry point"""
    console.print("[bold]ADB Enable Helper[/bold]\n")
    
    # Check current status
    connected, devices = check_adb_status()
    if connected:
        console.print("[green]✓ ADB is already connected![/green]")
        console.print(f"  Devices: {devices}")
        return
    
    # Ask user preference
    console.print("How would you like to connect your device?\n")
    console.print("1. [cyan]USB Debugging[/cyan] (Traditional, works on all Android versions)")
    console.print("2. [cyan]Wireless Debugging[/cyan] (No cable needed, requires Android 11+)\n")
    
    choice = Prompt.ask("Select an option", choices=["1", "2"], default="1")
    
    if choice == "1":
        success = guide_usb_debugging()
    else:
        success = guide_wireless_debugging()
    
    # Final check
    if not success:
        connected, devices = check_adb_status()
        if connected:
            console.print("\n[green]✓ Success! ADB is now connected![/green]")
        else:
            console.print("\n[red]✗ ADB still not connected.[/red]")
            console.print("\nTroubleshooting tips:")
            console.print("  • Make sure ADB is installed (run 'adb --version')")
            console.print("  • Try unplugging and reconnecting the USB cable")
            console.print("  • Check that you accepted the debugging authorization on your phone")
            console.print("  • For wireless: ensure both devices are on the same network")

if __name__ == "__main__":
    main()