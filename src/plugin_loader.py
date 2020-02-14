import socket
import json

from enum import Enum

class Commands(Enum):

    load_plugin = 0


class PluginLoaderConnector:

    def __init__(self, bot):
        self.bot = bot
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(self.bot.config.plugin_loader_address)

    async def send_command(self, command, *args):
        self.socket.send(
            self.bot.config.plugin_loader_owner_key.encode())
        
        json = {
            "Command": command.name,
            "Args": list(args)
        }

        self.socket.send(str(json).encode())
