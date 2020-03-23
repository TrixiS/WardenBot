import re

from .constants import StringConstants


class PseudoMember:

    __slots__ = ("id", "guild")

    def __init__(self, id, guild):
        self.id = id
        self.guild = guild


class ContextFormatter:

    pattern = re.compile(r"\{(.+?)\.(.+?)\}")

    def __init__(self, **context):
        self.ctx = context
        self.allowed_names = context.keys()

    def format(self, string):
        matched = self.pattern.findall(string)
        ignored = []

        for name, field in matched:
            name_field_pair = (name, field)

            if name_field_pair in ignored:
                continue
        
            if name in self.allowed_names and field in StringConstants.ALLOWED_FMT_FIELDS:
                value = getattr(self.ctx[name], field, None)
                
                if value is not None:
                    string = string.replace(
                        "{}{}.{}{}".format('{', name, field, '}'), 
                        str(value))

            ignored.append(name_field_pair)

        return string
