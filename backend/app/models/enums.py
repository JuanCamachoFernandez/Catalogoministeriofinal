import enum


class Role(str, enum.Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN_VICEMINISTERIO = "ADMIN_VICEMINISTERIO"
    EXPOSITOR = "EXPOSITOR"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


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


class ProductStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"


class DocumentType(str, enum.Enum):
    CI = "CI"
    NIT = "NIT"
    OTRO = "OTRO"
