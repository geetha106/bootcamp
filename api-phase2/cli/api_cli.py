#!/usr/bin/env python3
"""
CLI tool for managing API keys
"""
import typer
import yaml
import os
import secrets
import string
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
from typing import Optional

app = typer.Typer(help="Manage API keys for FigureX API")
console = Console()

SETTINGS_FILE = "settings.yaml"


def load_settings():
    """Load settings from YAML file"""
    try:
        with open(SETTINGS_FILE, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] Settings file '{SETTINGS_FILE}' not found.")
        raise typer.Exit(1)
    except yaml.YAMLError as e:
        console.print(f"[bold red]Error:[/bold red] Failed to parse settings file: {e}")
        raise typer.Exit(1)


def save_settings(settings):
    """Save settings to YAML file"""
    try:
        # Create a backup of the original file
        if os.path.exists(SETTINGS_FILE):
            backup_file = f"{SETTINGS_FILE}.bak"
            with open(SETTINGS_FILE, "r") as src, open(backup_file, "w") as dst:
                dst.write(src.read())
            
        with open(SETTINGS_FILE, "w") as f:
            yaml.dump(settings, f, default_flow_style=False)
            
        return True
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to save settings: {e}")
        return False


def generate_api_key(length=32):
    """Generate a random API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@app.command()
def show():
    """Show the current API key"""
    settings = load_settings()
    api_key = settings.get("api", {}).get("api_key", "")
    
    if not api_key or api_key == "changeme123":
        console.print("[bold yellow]Warning:[/bold yellow] No API key set or using default key.")
        console.print("Use the [bold]set[/bold] command to set a new API key.")
    else:
        # Show only the first and last 4 characters
        masked_key = f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"
        
        table = Table(show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("API Key", masked_key)
        table.add_row("Key Length", str(len(api_key)))
        
        console.print(Panel(table, title="API Key Information", border_style="blue"))
        
        console.print("\nUse the [bold]--reveal[/bold] option to show the full key.")


@app.command()
def reveal():
    """Reveal the full API key"""
    settings = load_settings()
    api_key = settings.get("api", {}).get("api_key", "")
    
    if not api_key or api_key == "changeme123":
        console.print("[bold yellow]Warning:[/bold yellow] No API key set or using default key.")
        console.print("Use the [bold]set[/bold] command to set a new API key.")
    else:
        table = Table(show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("API Key", api_key)
        table.add_row("Key Length", str(len(api_key)))
        
        console.print(Panel(table, title="API Key (SENSITIVE)", border_style="red"))
        
        console.print("\n[bold yellow]Warning:[/bold yellow] Keep this key secure!")


@app.command()
def set(
    key: Optional[str] = typer.Argument(None, help="The API key to set. If not provided, a random key will be generated."),
    length: int = typer.Option(32, "--length", "-l", help="Length of the generated API key")
):
    """Set a new API key"""
    settings = load_settings()
    
    # Generate a key if not provided
    if not key:
        key = generate_api_key(length)
        console.print(f"[bold green]Generated new API key[/bold green] of length {length}.")
    
    # Ensure api section exists
    if "api" not in settings:
        settings["api"] = {}
    
    # Store the old key for reference
    old_key = settings["api"].get("api_key", "")
    
    # Set the new key
    settings["api"]["api_key"] = key
    
    # Save settings
    if save_settings(settings):
        console.print("[bold green]API key updated successfully![/bold green]")
        
        # Show the new key
        table = Table(show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        # Show only the first and last 4 characters
        masked_key = f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"
        
        table.add_row("New API Key", masked_key)
        table.add_row("Key Length", str(len(key)))
        
        console.print(Panel(table, title="New API Key Information", border_style="blue"))
        console.print("\nUse the [bold]reveal[/bold] command to show the full key.")


@app.command()
def generate(
    length: int = typer.Option(32, "--length", "-l", help="Length of the API key"),
    save: bool = typer.Option(False, "--save", "-s", help="Save the generated key to settings")
):
    """Generate a new API key without saving it"""
    key = generate_api_key(length)
    
    if save:
        settings = load_settings()
        
        # Ensure api section exists
        if "api" not in settings:
            settings["api"] = {}
        
        # Set the new key
        settings["api"]["api_key"] = key
        
        # Save settings
        if save_settings(settings):
            console.print("[bold green]API key generated and saved successfully![/bold green]")
    else:
        console.print("[bold green]Generated API key:[/bold green]")
        console.print(Panel(key, border_style="green"))
        console.print("Use [bold]--save[/bold] option to save this key to settings.")


@app.command()
def reset():
    """Reset the API key to default"""
    settings = load_settings()
    
    # Ensure api section exists
    if "api" not in settings:
        settings["api"] = {}
    
    # Set the default key
    settings["api"]["api_key"] = "changeme123"
    
    # Save settings
    if save_settings(settings):
        console.print("[bold yellow]API key reset to default value.[/bold yellow]")
        console.print("This is not secure for production use!")


if __name__ == "__main__":
    app() 