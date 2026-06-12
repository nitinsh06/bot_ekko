#!/usr/bin/env python3
import cmd
import socket
import json
import sys

SOCKET_PATH = "/tmp/ekko_cli.sock"

class EkkoCLI(cmd.Cmd):
    intro = 'Welcome to the Ekko CLI. Type help or ? to list commands.\n'
    prompt = 'EKKO> '
    
    def __init__(self):
        super().__init__()
        self.sock = None
        self.connect()

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(2.0)
            print(f"Connecting to Ekko via {SOCKET_PATH}...")
            self.sock.connect(SOCKET_PATH)
            print("Connected!")
        except FileNotFoundError:
            print(f"Error: Could not find socket at {SOCKET_PATH}. Is Ekko running?")
            sys.exit(1)
        except ConnectionRefusedError:
            print("Error: Connection refused. Is Ekko's CLI Service enabled?")
            sys.exit(1)
        except Exception as e:
            print(f"Error connecting: {e}")
            sys.exit(1)

    def _send_command(self, command_name: str, params: dict):
        payload = {
            "command": command_name,
            "params": params
        }
        try:
            self.sock.sendall(json.dumps(payload).encode('utf-8'))
            response = self.sock.recv(4096)
            if response:
                result = json.loads(response.decode('utf-8'))
                if result.get("status") == "success":
                    print(f"Success: {result.get('message')}")
                else:
                    print(f"Error: {result.get('message')}")
            else:
                print("Error: Ekko unexpectedly closed the connection.")
                self.connect()
        except socket.timeout:
            print("Error: Ekko did not respond in time.")
        except Exception as e:
            print(f"Error communicating with Ekko: {e}")
            self.connect()

    def do_set_state(self, arg):
        """
        Forces Ekko into a specific state.
        Usage: set_state <STATE_NAME>
        Example: set_state ACTIVE
        """
        if not arg:
            print("Error: Please provide a target state. Example: set_state ACTIVE")
            return
        
        target_state = arg.strip().upper()
        self._send_command("change_state", {"target_state": target_state})

    def do_exit(self, arg):
        """Exit the CLI."""
        print("Goodbye!")
        if self.sock:
            self.sock.close()
        return True

    def do_EOF(self, arg):
        """Exit the CLI using Ctrl+D."""
        print()
        return self.do_exit(arg)

if __name__ == '__main__':
    try:
        EkkoCLI().cmdloop()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
