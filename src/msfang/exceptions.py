"""Domain exceptions for MsFang."""


class MsFangError(Exception):
    """Base domain exception."""


class StateTransitionError(MsFangError):
    """Raised when a ticket attempts an invalid state transition."""


class ApprovalError(MsFangError):
    """Raised when approval operations fail validation."""


class TicketNotFoundError(MsFangError):
    """Raised when a ticket id cannot be resolved from storage."""


class DelegationError(MsFangError):
    """Raised when a task violates hard delegation routing policy."""
