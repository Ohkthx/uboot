from typing import Optional

# 0: int  - guild_id
# 1: int  - id
# 2: str  - title
# 3: bool - done
TicketRaw = tuple[int, int, str, bool]


def make_raw(guild_id: int, id: int) -> TicketRaw:
    return (guild_id, id, "unknown", False)


class Ticket():
    def __init__(self, raw: TicketRaw) -> None:
        self.guild_id = raw[0]
        self.id = raw[1]
        self.title = raw[2].lower()
        self.done = raw[3]

    @property
    def _raw(self) -> TicketRaw:
        return (self.guild_id, self.id, self.title, self.done)

    @property
    def name(self) -> str:
        return f"{self.id}-{self.title}"


class Manager():
    _tickets: dict[int, dict[int, Ticket]] = {}

    @staticmethod
    def total(guild_id: int) -> int:
        guild_tickets = Manager._tickets.get(guild_id)
        if not guild_tickets:
            Manager._tickets[guild_id] = {}
            return 0

        return len(guild_tickets.keys())

    @staticmethod
    def add(ticket: Ticket) -> Ticket:
        guild_tickets = Manager._tickets.get(ticket.guild_id)
        if not guild_tickets:
            Manager._tickets[ticket.guild_id] = {}

        Manager._tickets[ticket.guild_id][ticket.id] = ticket
        return ticket

    @staticmethod
    def by_name(guild_id: int, name: str) -> Optional[Ticket]:
        guild_tickets = Manager._tickets.get(guild_id)
        if not guild_tickets:
            return None

        for value in guild_tickets.values():
            if value.name == name:
                return value
        return None

    @staticmethod
    def get(guild_id: int, id: int) -> Ticket:
        guild_tickets = Manager._tickets.get(guild_id)
        if not guild_tickets:
            ticket = Ticket(make_raw(guild_id, id))
            return Manager.add(ticket)

        ticket = guild_tickets.get(id)
        if not ticket:
            ticket = Ticket(make_raw(guild_id, id))
            Manager.add(ticket)
        return ticket
