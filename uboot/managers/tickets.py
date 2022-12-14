"""Tickets are support requests created by users for issues that need
to be resolved by others.
The associated manager handles all of the loading and saving to database. It is
also equpped with finding tickets based on certain parameters.
"""
from typing import Optional

from db.tickets import TicketDb, TicketRaw


def make_raw(guild_id: int, ticket_id: int) -> TicketRaw:
    """Creates a raw ticket (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return (guild_id, ticket_id, "unknown", False, 0)


class Ticket():
    """Representation of support tickets. Initialized with TicketRaw."""

    def __init__(self, raw: TicketRaw) -> None:
        self.guild_id = raw[0]
        self.id = raw[1]
        self.title = raw[2].lower()
        self.done = raw[3]
        self.owner_id = raw[4]

    @property
    def _raw(self) -> TicketRaw:
        """Converts the Ticket back into a TicketRaw"""
        return (self.guild_id, self.id, self.title, self.done, self.owner_id)

    @property
    def name(self) -> str:
        """Returns a pretty name for the Ticket."""
        return f"{self.id}-{self.title}"

    def save(self) -> None:
        """Stores the Ticket into the database, saving or updating
        as necessary.
        """
        if Manager._db:
            Manager._db.update(self._raw)


class Manager():
    """Manages the Ticket database in memory and in storage."""
    _db: Optional[TicketDb] = None
    _tickets: dict[int, dict[int, Ticket]] = {}

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the Ticket Manager, connecting and loading from
        database.
        """
        Manager._db = TicketDb(dbname)
        raw_tickets = Manager._db.find_all(incomplete_only=True)
        for raw in raw_tickets:
            Manager.add(Ticket(raw))

    @staticmethod
    def last_id(guild_id: int) -> int:
        """Gets the most recent Id created for a particular guild.
        Defaults to 0 if there is none."""
        if not Manager._db:
            raise ValueError("could not get last ticket id, no db.")

        last = Manager._db.find_last(guild_id)
        if last:
            return Ticket(last).id
        return 0

    @staticmethod
    def total(guild_id: int) -> int:
        """Get the current total tickets for a guild."""
        guild_tickets = Manager._tickets.get(guild_id)
        if not guild_tickets:
            # Initialize the guild.
            Manager._tickets[guild_id] = {}
            return 0

        return len(guild_tickets.keys())

    @staticmethod
    def add(ticket: Ticket) -> Ticket:
        """Adds a ticket to memory, does not save it to database."""
        guild_tickets = Manager._tickets.get(ticket.guild_id)
        if not guild_tickets:
            # Initialize the guild.
            Manager._tickets[ticket.guild_id] = {}

        # Create assign the ticket to the guild.
        Manager._tickets[ticket.guild_id][ticket.id] = ticket
        return ticket

    @staticmethod
    def by_name(guild_id: int, name: str) -> Optional[Ticket]:
        """Get a ticket from a guild based on its name."""
        guild_tickets = Manager._tickets.get(guild_id)
        if not guild_tickets:
            # No guild = no tickets.
            return None

        # Attempt to resolve the ticket by searching all tickets.
        for value in guild_tickets.values():
            if value.name == name:
                return value
        return None

    @staticmethod
    def get(guild_id: int, ticket_id: int) -> Ticket:
        """Get a ticket from a guild based on its id. If it does not exist,
        it will be initialized with defaults.
        """
        guild_tickets = Manager._tickets.get(guild_id)
        if not guild_tickets:
            # No tickets exist for the guild yet. Create, add, and return it.
            ticket = Ticket(make_raw(guild_id, ticket_id))
            return Manager.add(ticket)

        ticket = guild_tickets.get(ticket_id)
        if not ticket:
            # Ticket not found, create and add it.
            ticket = Ticket(make_raw(guild_id, ticket_id))
            Manager.add(ticket)
        return ticket
