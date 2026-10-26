from enum import StrEnum


class LabelKind(StrEnum):
    EXPENSE = "expense"
    SAVING = "saving"
    INVESTMENT = "investment"


class MovementType(StrEnum):
    ALLOCATION = "allocation"
    ADDITION = "addition"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
