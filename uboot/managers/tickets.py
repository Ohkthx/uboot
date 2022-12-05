from typing import Optional

from db.tickets import TicketDb, TicketRaw


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

    def save(self) -> None:
        if Manager._db:
            Manager._db.update(self._raw)


class Manager():
    _db: Optional[TicketDb] = None
    _tickets: dict[int, dict[int, Ticket]] = {}

    @staticmethod
    def init(dbname: str) -> None:
        Manager._db = TicketDb(dbname)
        raw_tickets = Manager._db.find_all(incomplete_only=True)
        for raw in raw_tickets:
            Manager.add(Ticket(raw))

    @staticmethod
    def last_id(guild_id: int) -> int:
        if not Manager._db:
            raise ValueError("could not get last ticket id, no db.")

        last = Manager._db.find_last(guild_id)
        if last:
            return Ticket(last).id
        return 0

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
