#!/usr/bin/env python3
"""Main CLI entry point for ADB Helper - Refactored with OoO"""

import click
from rich.console import Console
from .core.adb import ADBError
from .core.device import DeviceManager
from .commands import register_commands

console = Console()

@click.group()
@click.version_option()
@click.pass_context
def main(ctx):
    """ADB Helper - Simplify Android device management"""
    ctx.ensure_object(dict)
    try:
        ctx.obj['device_manager'] = DeviceManager()
    except ADBError as e:
        console.print(f"[red]Error: {e}[/red]")
        ctx.exit(1)

# Register all commands with the main group
register_commands(main)

if __name__ == "__main__":
    main()