import re

from itertools import chain
from .constants import StringConstants


class PseudoMember:

    __slots__ = ("id", "guild")

    def __init__(self, id, guild):
        self.id = id
        self.guild = guild


class ContextFormatter:

    pattern = re.compile(r"\{([a-zA-Z_\.]+?)\}")

    def __init__(self, *extra_fields, **context):
        self.ctx = context
        self.extra_fields = extra_fields

    @property
    def allowed_fields(self):
        return set(StringConstants.ALLOWED_FMT_FIELDS + self.extra_fields)

    def make_tag(self, *tokens):
        return '{' + '.'.join(tokens) + '}'

    def get_value(self, value_str):
        try:
            result = eval(value_str, self.ctx, self.ctx)
            return str(result)
        except Exception as e:
            return "None"

    def format(self, string):
        allowed_fields = self.allowed_fields

        for match in set(self.pattern.findall(string)):
            match = match.split('.')

            if len(match) == 0:
                continue

            name, *values = match

            if name not in self.ctx or any(value not in allowed_fields for value in values):
                continue
            
            tag = self.make_tag(name, *values)
            string = string.replace(tag, self.get_value(tag[1:-1]))

        return string
