import socket
import json
import subprocess

from enum import Enum


class Commands(Enum):

    load_plugin = 0


class PluginLoader:

    def __init__(self, bot):
        self.bot = bot
        self.process = subprocess.Popen(f"dotnet {self.bot.config.csharp_plugins_loader}" \
            f" {str(bot.assets_path / 'plugins')}" \
            f" {self.bot.config.plugin_loader_owner_key}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(self.bot.config.plugin_loader_address)

    def __del__(self):
        self.process.terminate()

    async def send_command(self, command, *args):
        self.socket.send(
            self.bot.config.plugin_loader_owner_key.encode())
        
        json = {
            "Command": command.name,
            "Args": list(args)
        }

        self.socket.send(str(json).encode())
