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


class AlertLevel(StrEnum):
    WARNING = "warning"  # 80% of the limit or more
    EXCEEDED = "exceeded"  # 100% or more


class GoalType(StrEnum):
    NORMAL = "normal"
    EMERGENCY_FUND = "emergency_fund"  # target = N months of average expenses
