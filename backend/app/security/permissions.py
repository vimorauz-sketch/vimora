"""Role -> permission matrix (least privilege). Seeded into the DB and also used in-process."""

from __future__ import annotations

from app.models.enums import RoleName

PERMISSIONS: dict[str, str] = {
    "orders.view": "View all orders",
    "orders.manage": "Change order status, notes and assignment",
    "orders.message": "Message customers on orders",
    "quotations.manage": "Create and revise quotations",
    "deliverables.manage": "Upload, approve and release deliverables",
    "services.manage": "Manage services, categories and pricing",
    "customers.view": "View customer profiles",
    "customers.manage": "Disable/restore customer accounts",
    "finance.view": "View payments, revenue and reports",
    "finance.manage": "Record manual payments and process refunds",
    "ai.view": "View AI executions and logs",
    "ai.operate": "Trigger, retry, approve or reject AI executions",
    "ai.configure": "Configure AI providers, models and budgets",
    "settings.manage": "Change system settings and content pages",
    "secrets.manage": "Set integration secrets (API keys, tokens)",
    "staff.manage": "Grant and revoke staff roles",
    "audit.view": "View audit logs",
    "analytics.view": "View analytics dashboards",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    RoleName.SUPER_ADMIN: set(PERMISSIONS),
    RoleName.ADMIN: set(PERMISSIONS) - {"secrets.manage", "staff.manage"},
    # Support: no finance, no infrastructure/secret management, no service pricing.
    RoleName.SUPPORT: {"orders.view", "orders.message", "customers.view", "ai.view"},
    RoleName.CUSTOMER: set(),
}

STAFF_ROLES = {RoleName.SUPER_ADMIN, RoleName.ADMIN, RoleName.SUPPORT}


def permissions_for(role_names: set[str]) -> set[str]:
    out: set[str] = set()
    for r in role_names:
        out |= ROLE_PERMISSIONS.get(r, set())
    return out
