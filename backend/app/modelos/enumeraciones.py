import enum


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    PRODUCTIVE_UNIT_RESPONSIBLE = "PRODUCTIVE_UNIT_RESPONSIBLE"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"
    BLOCKED = "BLOCKED"


class FeriaStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    DISABLED = "DISABLED"
    FINISHED = "FINISHED"


class AssignmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    INACTIVE = "INACTIVE"


class ProductStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    AVAILABLE = "AVAILABLE"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    RETIRED = "RETIRED"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"


class RegistrationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProductiveUnitStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class SectorStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class DocumentType(str, enum.Enum):
    CI = "CI"
    NIT = "NIT"
    OTRO = "OTRO"
