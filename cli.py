"""
Command Line Interface for Mainframe Copilot
Interactive and batch mode support for mainframe operations
"""

import click
import asyncio
import logging
import sys
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.logging import RichHandler

from tn3270.client import TN3270Client
from tn3270.parser import ScreenParser, ScreenType
from tn3270.commands import CommandBuilder
from ai.llm_handler import LLMHandler
from config.settings import Settings

# Setup rich console
console = Console()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)


class MainframeCLI:
    """Interactive CLI for mainframe operations"""

    def __init__(self, host: str = "localhost", port: int = 3270):
        """
        Initialize CLI

        Args:
            host: Mainframe host
            port: 3270 port
        """
        self.host = host
        self.port = port
        self.client = TN3270Client(host, port)
        self.parser = ScreenParser()
        self.command_builder = CommandBuilder()
        self.llm_handler = None
        self.connected = False
        self.logged_on = False
        self.settings = Settings()

    async def connect(self) -> bool:
        """
        Connect to mainframe

        Returns:
            bool: Success status
        """
        with console.status(f"Connecting to {self.host}:{self.port}..."):
            self.connected = await self.client.connect()

        if self.connected:
            console.print(f" Connected to {self.host}:{self.port}", style="green")
        else:
            console.print(f"L Failed to connect to {self.host}:{self.port}", style="red")

        return self.connected

    async def logon(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Logon to TSO

        Args:
            username: TSO username
            password: TSO password

        Returns:
            bool: Success status
        """
        if not self.connected:
            console.print("L Not connected to mainframe", style="red")
            return False

        # Get credentials if not provided
        if not username:
            username = Prompt.ask("Enter TSO username", default="HERC01")
        if not password:
            password = Prompt.ask("Enter password", password=True, default="CUL8TR")

        with console.status(f"Logging on as {username}..."):
            self.logged_on = await self.client.logon(username, password)

        if self.logged_on:
            console.print(f" Logged on as {username}", style="green")
        else:
            console.print(f"L Logon failed", style="red")

        return self.logged_on

    async def execute_command(self, command: str) -> str:
        """
        Execute TSO command

        Args:
            command: Command to execute

        Returns:
            str: Command output
        """
        if not self.logged_on:
            console.print("L Not logged on to TSO", style="red")
            return ""

        with console.status(f"Executing: {command}"):
            output = await self.client.execute_tso_command(command)

        return output

    def display_screen(self):
        """Display current screen content"""
        if not self.connected:
            console.print("L Not connected", style="red")
            return

        screen_content = self.client.get_screen()
        screen_info = self.parser.parse_screen(screen_content)

        # Create panel with screen content
        panel = Panel(
            screen_content,
            title=f"Screen Type: {screen_info.type.value}",
            border_style="blue"
        )
        console.print(panel)

        # Show messages if any
        if screen_info.messages:
            console.print("\n[yellow]Messages:[/yellow]")
            for msg in screen_info.messages:
                console.print(f"  " {msg}")

    def display_dataset_list(self, datasets):
        """
        Display dataset list in table format

        Args:
            datasets: List of datasets
        """
        table = Table(title="Dataset List")
        table.add_column("Dataset Name", style="cyan")
        table.add_column("Volume", style="magenta")
        table.add_column("DSORG", style="green")
        table.add_column("RECFM", style="yellow")

        for ds in datasets:
            table.add_row(
                ds.get('name', ''),
                ds.get('volume', ''),
                ds.get('dsorg', ''),
                ds.get('recfm', '')
            )

        console.print(table)

    def display_jcl(self, jcl: str):
        """
        Display JCL with syntax highlighting

        Args:
            jcl: JCL content
        """
        syntax = Syntax(jcl, "text", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Generated JCL", border_style="green"))

    async def interactive_mode(self):
        """Run interactive command loop"""
        console.print(Panel.fit(
            "[bold cyan]Mainframe Copilot - Interactive Mode[/bold cyan]\n"
            "Type 'help' for commands, 'quit' to exit",
            border_style="cyan"
        ))

        while True:
            try:
                command = Prompt.ask("\n[cyan]mainframe>[/cyan]")

                if not command:
                    continue

                # Parse command
                cmd_parts = command.lower().split()
                cmd = cmd_parts[0]

                # Handle built-in commands
                if cmd == 'quit' or cmd == 'exit':
                    if Confirm.ask("Do you want to exit?"):
                        break

                elif cmd == 'help':
                    self.show_help()

                elif cmd == 'connect':
                    await self.connect()

                elif cmd == 'logon':
                    await self.logon()

                elif cmd == 'logoff':
                    if self.logged_on:
                        await self.client.logoff()
                        self.logged_on = False
                        console.print(" Logged off", style="green")

                elif cmd == 'screen':
                    self.display_screen()

                elif cmd == 'clear':
                    if self.connected:
                        await self.client.send_clear()
                        console.print(" Screen cleared", style="green")

                elif cmd.startswith('pf'):
                    # Handle PF keys (pf3, pf12, etc.)
                    try:
                        pf_num = int(cmd[2:])
                        await self.client.send_pf(pf_num)
                        self.display_screen()
                    except ValueError:
                        console.print("L Invalid PF key", style="red")

                elif cmd == 'listds':
                    if len(cmd_parts) > 1:
                        pattern = cmd_parts[1].upper()
                        tso_cmd = self.command_builder.build_listds(pattern)
                        output = await self.execute_command(tso_cmd)
                        console.print(output)
                    else:
                        console.print("Usage: listds <dataset-pattern>", style="yellow")

                elif cmd == 'listcat':
                    if len(cmd_parts) > 1:
                        level = cmd_parts[1].upper()
                        tso_cmd = self.command_builder.build_listcat(level=level)
                        output = await self.execute_command(tso_cmd)
                        console.print(output)
                    else:
                        console.print("Usage: listcat <level>", style="yellow")

                elif cmd == 'submit':
                    if len(cmd_parts) > 1:
                        dataset = ' '.join(cmd_parts[1:])
                        tso_cmd = self.command_builder.build_submit(dataset)
                        output = await self.execute_command(tso_cmd)
                        console.print(output)
                    else:
                        console.print("Usage: submit <dataset>", style="yellow")

                elif cmd == 'status':
                    tso_cmd = self.command_builder.build_status()
                    output = await self.execute_command(tso_cmd)
                    console.print(output)

                elif cmd == 'tso':
                    # Direct TSO command
                    if len(cmd_parts) > 1:
                        tso_cmd = ' '.join(cmd_parts[1:]).upper()
                        output = await self.execute_command(tso_cmd)
                        console.print(output)
                    else:
                        console.print("Usage: tso <command>", style="yellow")

                elif cmd == 'ai' or cmd == 'ask':
                    # AI assistant mode
                    if len(cmd_parts) > 1:
                        query = ' '.join(cmd_parts[1:])
                        await self.handle_ai_query(query)
                    else:
                        console.print("Usage: ai <your question>", style="yellow")

                else:
                    # Try as direct TSO command
                    if self.logged_on:
                        output = await self.execute_command(command.upper())
                        console.print(output)
                    else:
                        console.print(f"L Unknown command: {cmd}", style="red")
                        console.print("Type 'help' for available commands", style="yellow")

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'quit' to exit[/yellow]")
            except Exception as e:
                console.print(f"L Error: {e}", style="red")
                logger.exception("Command error")

    def show_help(self):
        """Display help information"""
        help_text = """
[bold cyan]Available Commands:[/bold cyan]

[yellow]Connection:[/yellow]
  connect              - Connect to mainframe
  logon                - Logon to TSO
  logoff               - Logoff from TSO
  quit/exit            - Exit the program

[yellow]Screen Control:[/yellow]
  screen               - Display current screen
  clear                - Clear screen
  pf<n>                - Send PF key (e.g., pf3, pf12)

[yellow]TSO Commands:[/yellow]
  listds <pattern>     - List datasets
  listcat <level>      - List catalog entries
  submit <dataset>     - Submit JCL
  status               - Show job status
  tso <command>        - Execute TSO command

[yellow]AI Assistant:[/yellow]
  ai <question>        - Ask AI for help
  ask <question>       - Same as 'ai'

[yellow]Examples:[/yellow]
  listds SYS1.*        - List SYS1 datasets
  submit HERC01.JCL(TEST) - Submit TEST member
  ai create JCL to copy dataset - Get AI help
        """
        console.print(help_text)

    async def handle_ai_query(self, query: str):
        """
        Handle AI assistant query

        Args:
            query: User query
        """
        if not self.llm_handler:
            console.print("L AI assistant not configured", style="red")
            return

        with console.status("Thinking..."):
            response = await self.llm_handler.process_query(query)

        console.print(Panel(response, title="AI Assistant", border_style="green"))


@click.command()
@click.option('--host', '-h', default='localhost', help='Mainframe host')
@click.option('--port', '-p', default=3270, type=int, help='3270 port')
@click.option('--username', '-u', help='TSO username')
@click.option('--password', '-pw', help='TSO password')
@click.option('--command', '-c', help='Execute command and exit')
@click.option('--batch', '-b', type=click.File('r'), help='Batch command file')
@click.option('--ai', is_flag=True, help='Enable AI assistant')
def main(host, port, username, password, command, batch, ai):
    """Mainframe Copilot - AI-powered mainframe assistant"""

    # Create CLI instance
    cli = MainframeCLI(host, port)

    # Enable AI if requested
    if ai:
        try:
            from ai.llm_handler import LLMHandler
            cli.llm_handler = LLMHandler()
            console.print(" AI assistant enabled", style="green")
        except Exception as e:
            console.print(f"  AI assistant not available: {e}", style="yellow")

    async def run():
        """Main async runner"""
        # Connect to mainframe
        if not await cli.connect():
            return 1

        # Logon if credentials provided
        if username:
            if not await cli.logon(username, password):
                return 1

        # Handle different modes
        if command:
            # Single command mode
            output = await cli.execute_command(command)
            console.print(output)

        elif batch:
            # Batch mode
            console.print(f"=Ë Executing batch file: {batch.name}", style="cyan")
            for line in batch:
                line = line.strip()
                if line and not line.startswith('#'):
                    console.print(f"’ {line}", style="blue")
                    output = await cli.execute_command(line)
                    console.print(output)

        else:
            # Interactive mode
            await cli.interactive_mode()

        # Disconnect
        await cli.client.disconnect()
        return 0

    # Run the async function
    sys.exit(asyncio.run(run()))


if __name__ == '__main__':
    main()