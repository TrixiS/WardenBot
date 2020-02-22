import typing

from cogs.utils.db import DbType


class Config:
    
    # C# settings
    use_csharp_plugins: bool = True
    csharp_plugins_loader: str = r""
    plugin_loader_owner_key: str = ""
    plugin_loader_address: typing.Tuple[typing.Union[str, int]] = ("127.0.0.1", 6969)

    # tokens
    bot_token: str = ""
    twitch_client_id: str = ""

    # bot defaults
    prefixes: typing.Tuple[str] = ("w!", )
    owners: typing.Tuple[int] = tuple()
    default_cooldown: typing.Tuple[int] = (1, 600)
    default_color: str = "255;255;255"
    default_lang: str = "en"
    status = "w!help | v2.0"

    # database settings
    db_type: DbType = DbType.SQLite
    database_settings: typing.Dict[str, typing.Union[str, int, bool]] = {
        "host": "localhost",
        "user": "",
        "password": "",
        "database": "",
        "port": 3306,

        # only for SQLite
        "check_same_thread": False
    }

    def to_dict(self, *keys) -> dict:
        return {k: getattr(self, k) for k in keys}