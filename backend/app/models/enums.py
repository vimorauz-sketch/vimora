from enum import StrEnum


class RoleName(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    SUPPORT = "SUPPORT"
    CUSTOMER = "CUSTOMER"


class OrderStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    QUOTATION_PENDING = "QUOTATION_PENDING"
    QUOTATION_ACCEPTED = "QUOTATION_ACCEPTED"
    DEPOSIT_PENDING = "DEPOSIT_PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    QUEUED = "QUEUED"
    AI_PROCESSING = "AI_PROCESSING"
    AI_REVIEW_REQUIRED = "AI_REVIEW_REQUIRED"
    MANUAL_PROCESSING = "MANUAL_PROCESSING"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    COMPLETED_PENDING_FINAL_PAYMENT = "COMPLETED_PENDING_FINAL_PAYMENT"
    FINAL_PAYMENT_PENDING = "FINAL_PAYMENT_PENDING"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class PricingType(StrEnum):
    FIXED = "FIXED"
    PER_UNIT = "PER_UNIT"
    QUANTITY_TIERED = "QUANTITY_TIERED"
    STARTING_FROM = "STARTING_FROM"
    CUSTOM_QUOTE = "CUSTOM_QUOTE"


class DepositType(StrEnum):
    PERCENT = "PERCENT"
    FIXED = "FIXED"


class QuotationStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"


class PaymentKind(StrEnum):
    DEPOSIT = "DEPOSIT"
    FINAL = "FINAL"
    FULL = "FULL"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"  # provider has created/held the transaction
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentProvider(StrEnum):
    CLICK = "CLICK"
    PAYME = "PAYME"
    STRIPE = "STRIPE"
    MANUAL = "MANUAL"


class RefundStatus(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class ExecutionMethod(StrEnum):
    UNASSIGNED = "UNASSIGNED"
    AI = "AI"
    MANUAL = "MANUAL"


class AIExecutionStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AttachmentPurpose(StrEnum):
    ORDER_INPUT = "ORDER_INPUT"
    MESSAGE = "MESSAGE"
    DELIVERABLE = "DELIVERABLE"
    AI_OUTPUT = "AI_OUTPUT"
    SERVICE_IMAGE = "SERVICE_IMAGE"
    BRANDING = "BRANDING"


class ScanStatus(StrEnum):
    NOT_SCANNED = "NOT_SCANNED"
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    ERROR = "ERROR"


class NotificationChannel(StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    TELEGRAM = "TELEGRAM"
    ADMIN_FEED = "ADMIN_FEED"  # in-app staff activity feed (admin panel bell + sound)


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"  # e.g. channel not configured / user opted out
    LOGGED_DEV = "LOGGED_DEV"  # development console backend, not actually delivered


class ActorType(StrEnum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"
    PAYMENT = "PAYMENT"  # trusted, verified payment events only
    AI = "AI"


class ServiceMode(StrEnum):
    """How (and where) a service is delivered."""

    ONLINE = "ONLINE"  # done over the internet, anywhere in Uzbekistan
    REMOTE = "REMOTE"  # remote technical help on the customer's computer (with consent, e.g. AnyDesk)
    LOCAL = "LOCAL"  # needs physical presence/equipment; only inside the service's area
    FUTURE = "FUTURE"  # planned (partners later); hidden from the catalog
    DISABLED = "DISABLED"  # duplicate/unsuitable; archived, kept for history


class AreaKind(StrEnum):
    REGION = "REGION"  # viloyat
    DISTRICT = "DISTRICT"  # tuman
    LOCALITY = "LOCALITY"  # shahar / qishloq
    OTHER = "OTHER"  # "other regions of Uzbekistan"


class HandoverMethod(StrEnum):
    PICKUP = "PICKUP"
    MEETUP = "MEETUP"


class HandoverStatus(StrEnum):
    """Physical handover of LOCAL orders. Deliberately separate from order/payment statuses."""

    WAITING = "WAITING"  # pickup: work not finished yet
    PROPOSED_BY_CUSTOMER = "PROPOSED_BY_CUSTOMER"  # meetup place/time suggested by the customer
    PROPOSED_BY_ADMIN = "PROPOSED_BY_ADMIN"  # owner suggested a different place/time
    CONFIRMED = "CONFIRMED"  # meetup agreed by both sides
    READY_FOR_PICKUP = "READY_FOR_PICKUP"  # pickup: ready, customer may come
    HANDED_OVER = "HANDED_OVER"
