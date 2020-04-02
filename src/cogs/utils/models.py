import re

from itertools import chain
from .constants import StringConstants


class PseudoMember:

    __slots__ = ("id", "guild")

    def __init__(self, id, guild):
        self.id = id
        self.guild = guild


class ContextFormatter:

    pattern = re.compile(r"\{(.+?)\.(.+?)\}")

    def __init__(self, *extra_fields, **context):
        self.ctx = context
        self.extra_fields = extra_fields

    @property
    def allowed_names(self):
        return chain(self.ctx.keys(), self.extra_fields)

    def format(self, string):
        matched = self.pattern.findall(string)

        for name, field in set(matched):
            if name in self.allowed_names and field in StringConstants.ALLOWED_FMT_FIELDS:
                value = getattr(self.ctx[name], field, None)
                
                if value is not None:
                    string = string.replace(
                        "{}{}.{}{}".format('{', name, field, '}'), 
                        str(value))

        return string
