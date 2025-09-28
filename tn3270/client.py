"""
TN3270 Client Implementation for Mainframe Interaction
Handles connection, screen management, and basic 3270 protocol operations
"""

import asyncio
import logging
from typing import Optional, Tuple, List, Dict, Any
from py3270 import Emulator
import time

logger = logging.getLogger(__name__)


class TN3270Client:
    """Wrapper for py3270 emulator with async support and enhanced functionality"""

    def __init__(self, host: str = "localhost", port: int = 3270, timeout: int = 30):
        """
        Initialize TN3270 client

        Args:
            host: Mainframe host address
            port: TN3270 port (default 3270)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.emulator: Optional[Emulator] = None
        self.connected = False
        self.screen_size = (24, 80)  # Standard 3270 Model 2

    async def connect(self) -> bool:
        """
        Establish connection to mainframe

        Returns:
            bool: True if connection successful
        """
        try:
            # Initialize emulator
            self.emulator = Emulator(visible=False, timeout=self.timeout)

            # Connect to host
            connection_string = f"{self.host}:{self.port}"
            logger.info(f"Connecting to {connection_string}")

            self.emulator.connect(connection_string)

            # Wait for connection to establish
            await asyncio.sleep(1)

            # Check connection status
            if self.emulator.is_connected():
                self.connected = True
                logger.info(f"Successfully connected to {connection_string}")
                return True
            else:
                logger.error(f"Failed to connect to {connection_string}")
                return False

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    async def disconnect(self):
        """Disconnect from mainframe"""
        if self.emulator and self.connected:
            try:
                self.emulator.terminate()
                self.connected = False
                logger.info("Disconnected from mainframe")
            except Exception as e:
                logger.error(f"Disconnect error: {e}")

    def get_screen(self) -> str:
        """
        Get current screen content as string

        Returns:
            str: Screen content
        """
        if not self.emulator:
            return ""

        try:
            return self.emulator.string_get(1, 1, *self.screen_size)
        except Exception as e:
            logger.error(f"Error getting screen: {e}")
            return ""

    def get_screen_array(self) -> List[str]:
        """
        Get screen content as array of lines

        Returns:
            List[str]: Screen lines
        """
        screen = self.get_screen()
        if not screen:
            return []

        lines = []
        rows, cols = self.screen_size

        for i in range(rows):
            start = i * cols
            end = start + cols
            line = screen[start:end] if start < len(screen) else ""
            lines.append(line.rstrip())

        return lines

    async def send_string(self, text: str):
        """
        Send string to mainframe

        Args:
            text: Text to send
        """
        if not self.emulator:
            raise RuntimeError("Not connected to mainframe")

        try:
            self.emulator.send_string(text)
            await asyncio.sleep(0.1)  # Small delay for processing
        except Exception as e:
            logger.error(f"Error sending string: {e}")
            raise

    async def send_enter(self):
        """Send ENTER key"""
        if not self.emulator:
            raise RuntimeError("Not connected to mainframe")

        try:
            self.emulator.send_enter()
            await asyncio.sleep(0.5)  # Wait for screen update
        except Exception as e:
            logger.error(f"Error sending enter: {e}")
            raise

    async def send_pf(self, key_number: int):
        """
        Send PF key (1-24)

        Args:
            key_number: PF key number
        """
        if not self.emulator:
            raise RuntimeError("Not connected to mainframe")

        if not 1 <= key_number <= 24:
            raise ValueError(f"Invalid PF key number: {key_number}")

        try:
            self.emulator.send_pf(key_number)
            await asyncio.sleep(0.5)  # Wait for screen update
        except Exception as e:
            logger.error(f"Error sending PF{key_number}: {e}")
            raise

    async def send_clear(self):
        """Send CLEAR key"""
        if not self.emulator:
            raise RuntimeError("Not connected to mainframe")

        try:
            self.emulator.send_clear()
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending clear: {e}")
            raise

    async def wait_for_field(self) -> bool:
        """
        Wait for input field to be ready

        Returns:
            bool: True if field is ready
        """
        if not self.emulator:
            return False

        max_wait = 10  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                status = self.emulator.status()
                if status and status.field_protection == 'U':  # Unprotected field
                    return True
            except:
                pass

            await asyncio.sleep(0.2)

        return False

    async def wait_for_text(self, text: str, timeout: int = 10) -> bool:
        """
        Wait for specific text to appear on screen

        Args:
            text: Text to wait for
            timeout: Maximum wait time in seconds

        Returns:
            bool: True if text found
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            screen = self.get_screen()
            if text in screen:
                return True
            await asyncio.sleep(0.5)

        return False

    def find_text(self, text: str) -> Optional[Tuple[int, int]]:
        """
        Find text position on screen

        Args:
            text: Text to find

        Returns:
            Optional[Tuple[int, int]]: (row, column) position or None
        """
        screen = self.get_screen()
        if not screen or text not in screen:
            return None

        index = screen.find(text)
        if index == -1:
            return None

        cols = self.screen_size[1]
        row = index // cols + 1
        col = index % cols + 1

        return (row, col)

    def get_cursor_position(self) -> Tuple[int, int]:
        """
        Get current cursor position

        Returns:
            Tuple[int, int]: (row, column) position
        """
        if not self.emulator:
            return (1, 1)

        try:
            status = self.emulator.status()
            if status:
                return (status.cursor_row, status.cursor_column)
        except:
            pass

        return (1, 1)

    def move_cursor(self, row: int, col: int):
        """
        Move cursor to specific position

        Args:
            row: Target row (1-based)
            col: Target column (1-based)
        """
        if not self.emulator:
            raise RuntimeError("Not connected to mainframe")

        try:
            self.emulator.move_to(row, col)
        except Exception as e:
            logger.error(f"Error moving cursor: {e}")
            raise

    async def logon(self, username: str, password: str) -> bool:
        """
        Perform TSO logon

        Args:
            username: TSO user ID
            password: User password

        Returns:
            bool: True if logon successful
        """
        try:
            # Wait for initial screen
            await self.wait_for_field()

            # Clear screen if needed
            await self.send_clear()
            await asyncio.sleep(1)

            # Send LOGON command
            logon_cmd = f"LOGON {username}"
            await self.send_string(logon_cmd)
            await self.send_enter()

            # Wait for password prompt
            if await self.wait_for_text("PASSWORD", timeout=5):
                # Send password
                await self.send_string(password)
                await self.send_enter()

                # Wait for READY prompt or logon messages
                if await self.wait_for_text("READY", timeout=15):
                    logger.info(f"Successfully logged on as {username}")
                    return True
                elif await self.wait_for_text("LOGON", timeout=5):
                    # Check for logon messages that might need acknowledgment
                    await self.send_enter()
                    if await self.wait_for_text("READY", timeout=10):
                        logger.info(f"Successfully logged on as {username}")
                        return True

            logger.error("Logon failed - timeout or invalid credentials")
            return False

        except Exception as e:
            logger.error(f"Logon error: {e}")
            return False

    async def logoff(self) -> bool:
        """
        Perform TSO logoff

        Returns:
            bool: True if logoff successful
        """
        try:
            await self.send_string("LOGOFF")
            await self.send_enter()
            await asyncio.sleep(2)
            logger.info("Logged off from TSO")
            return True
        except Exception as e:
            logger.error(f"Logoff error: {e}")
            return False

    async def execute_tso_command(self, command: str) -> str:
        """
        Execute a TSO command and return output

        Args:
            command: TSO command to execute

        Returns:
            str: Command output
        """
        try:
            # Clear screen for clean output
            await self.send_clear()
            await asyncio.sleep(0.5)

            # Send command
            await self.send_string(command)
            await self.send_enter()

            # Wait for command to complete
            await asyncio.sleep(2)

            # Get screen output
            return self.get_screen()

        except Exception as e:
            logger.error(f"Error executing TSO command: {e}")
            raise

    def __enter__(self):
        """Context manager entry"""
        asyncio.run(self.connect())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        asyncio.run(self.disconnect())

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()