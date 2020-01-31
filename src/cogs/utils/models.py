

class PseudoMember:

    __slots__ = ("id", "guild")

    def __init__(self, id, guild):
        self.id = id
        self.guild = guild