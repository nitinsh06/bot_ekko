import json
import socket
import os
import threading
from typing import Optional

from bot_ekko.core.base import ThreadedService
from bot_ekko.core.models import ServiceCliConfig, CommandNames
from bot_ekko.core.command_center import CommandCenter


class CLIService(ThreadedService):
    """
    Service that exposes a UNIX socket to receive commands from a CLI client.
    """
    def __init__(self, command_center: CommandCenter, config: ServiceCliConfig):
        super().__init__(config.name, enabled=config.enabled)
        self.command_center = command_center
        self.config = config
        self.socket_path = config.socket_path
        self.server_socket: Optional[socket.socket] = None

    def init(self) -> None:
        self.logger.info(f"CLI Service initialized. Socket: {self.socket_path}")
        super().init()

    def _run(self) -> None:
        # Cleanup any existing socket file
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(1)
        self.server_socket.settimeout(1.0) # Allows checking for stop event

        self.logger.info("CLI Service Loop Started")

        while not self._stop_event.is_set():
            try:
                conn, _ = self.server_socket.accept()
                self._handle_client(conn)
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Error in CLI Service loop: {e}")
                self.increment_stat("errors")
                
    def _handle_client(self, conn: socket.socket) -> None:
        with conn:
            conn.settimeout(2.0)
            try:
                data = conn.recv(4096)
                if not data:
                    return
                
                payload = json.loads(data.decode("utf-8"))
                cmd_name_str = payload.get("command")
                params = payload.get("params", {})

                if not cmd_name_str:
                    response = {"status": "error", "message": "No command provided"}
                    conn.sendall(json.dumps(response).encode("utf-8"))
                    return
                
                try:
                    cmd_name = CommandNames(cmd_name_str)
                    self.command_center.issue_command(cmd_name, params=params)
                    self.increment_stat("commands_received")
                    response = {"status": "success", "message": f"Command {cmd_name_str} dispatched."}
                except ValueError:
                    response = {"status": "error", "message": f"Unknown command: {cmd_name_str}"}

                conn.sendall(json.dumps(response).encode("utf-8"))

            except json.JSONDecodeError:
                response = {"status": "error", "message": "Invalid JSON format"}
                conn.sendall(json.dumps(response).encode("utf-8"))
            except socket.timeout:
                self.logger.warning("CLI socket read timeout")
            except Exception as e:
                self.logger.error(f"Error handling CLI client: {e}")
                
    def stop(self) -> None:
        super().stop()
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except Exception:
                pass

    def update(self) -> None:
        pass
