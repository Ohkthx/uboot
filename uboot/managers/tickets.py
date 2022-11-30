from typing import Optional

# 0: int  - id
# 1: str  - title
# 2: bool - done
TicketRaw = tuple[int, str, bool]


def make_raw(id: int) -> TicketRaw:
    return (id, "", False)


class Ticket():
    def __init__(self, raw: TicketRaw) -> None:
        self.id = raw[0]
        self.title = raw[1]
        self.done = raw[2]

    @property
    def _raw(self) -> TicketRaw:
        return (self.id, self.title, self.done)


class Manager():
    _tickets: dict[int, Ticket] = {}

    @staticmethod
    def total() -> int:
        return len(Manager._tickets.keys())

    @staticmethod
    def add(ticket: Ticket) -> Ticket:
        Manager._tickets[ticket.id] = ticket
        return ticket

    @staticmethod
    def by_title(title: str) -> Optional[Ticket]:
        for value in Manager._tickets.values():
            if value.title == title:
                return value

    @staticmethod
    def get(id: int) -> Ticket:
        setting = Manager._tickets.get(id)
        if not setting:
            setting = Ticket(make_raw(id))
            Manager.add(setting)
        return setting
