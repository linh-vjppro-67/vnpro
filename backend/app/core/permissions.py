from enum import StrEnum


class Permission(StrEnum):
    DASHBOARD_READ = "dashboard:read"
    SALES_READ = "sales:read"
    SALES_WRITE = "sales:write"
    SALES_APPROVE = "sales:approve"
    COST_READ = "cost:read"
    COST_WRITE = "cost:write"
    COST_APPROVE = "cost:approve"
    OPERATIONS_READ = "operations:read"
    OPERATIONS_WRITE = "operations:write"
    OPERATIONS_APPROVE = "operations:approve"
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"
    PURCHASE_READ = "purchase:read"
    PURCHASE_WRITE = "purchase:write"
    PURCHASE_APPROVE = "purchase:approve"
    FINANCE_READ = "finance:read"
    FINANCE_WRITE = "finance:write"
    SUPPORT_READ = "support:read"
    SUPPORT_WRITE = "support:write"
    INTEGRATION_RUN = "integration:run"
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"


ALL = {p.value for p in Permission}
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "SYSTEM_ADMIN": ALL,
    "DIRECTOR": ALL,
    "DIRECTOR_ASSISTANT": {Permission.DASHBOARD_READ, Permission.SALES_READ, Permission.COST_READ, Permission.OPERATIONS_READ, Permission.INVENTORY_READ, Permission.FINANCE_READ, Permission.SUPPORT_READ, Permission.AUDIT_READ},
    "MARKETING": {Permission.DASHBOARD_READ, Permission.SALES_READ, Permission.SALES_WRITE},
    "SALES": {Permission.DASHBOARD_READ, Permission.SALES_READ, Permission.SALES_WRITE, Permission.OPERATIONS_READ, Permission.INVENTORY_READ, Permission.FINANCE_READ, Permission.SUPPORT_READ, Permission.SUPPORT_WRITE},
    "SALES_ADMIN": {Permission.DASHBOARD_READ, Permission.SALES_READ, Permission.SALES_WRITE, Permission.SALES_APPROVE, Permission.OPERATIONS_READ, Permission.OPERATIONS_WRITE, Permission.INVENTORY_READ, Permission.FINANCE_READ, Permission.SUPPORT_READ},
    "TECH_SOLUTION": {Permission.DASHBOARD_READ, Permission.SALES_READ, Permission.OPERATIONS_READ, Permission.OPERATIONS_WRITE, Permission.OPERATIONS_APPROVE, Permission.INVENTORY_READ, Permission.PURCHASE_READ, Permission.PURCHASE_WRITE, Permission.SUPPORT_READ, Permission.SUPPORT_WRITE},
    "TECH_FIELD": {Permission.DASHBOARD_READ, Permission.OPERATIONS_READ, Permission.OPERATIONS_WRITE, Permission.INVENTORY_READ, Permission.PURCHASE_READ, Permission.PURCHASE_WRITE, Permission.SUPPORT_READ, Permission.SUPPORT_WRITE},
    "ACCOUNTING": {Permission.DASHBOARD_READ, Permission.SALES_READ, Permission.COST_READ, Permission.COST_WRITE, Permission.OPERATIONS_READ, Permission.INVENTORY_READ, Permission.PURCHASE_READ, Permission.FINANCE_READ, Permission.FINANCE_WRITE, Permission.INTEGRATION_RUN, Permission.AUDIT_READ},
    "PURCHASING": {Permission.DASHBOARD_READ, Permission.SALES_READ, Permission.COST_READ, Permission.COST_WRITE, Permission.OPERATIONS_READ, Permission.INVENTORY_READ, Permission.INVENTORY_WRITE, Permission.PURCHASE_READ, Permission.PURCHASE_WRITE},
    "WAREHOUSE": {Permission.DASHBOARD_READ, Permission.SALES_READ, Permission.OPERATIONS_READ, Permission.INVENTORY_READ, Permission.INVENTORY_WRITE, Permission.PURCHASE_READ, Permission.PURCHASE_WRITE},
    "CASHIER": {Permission.DASHBOARD_READ, Permission.COST_READ, Permission.COST_WRITE, Permission.FINANCE_READ, Permission.FINANCE_WRITE},
    "HCVP": {Permission.DASHBOARD_READ, Permission.COST_READ, Permission.COST_WRITE, Permission.INVENTORY_READ, Permission.USERS_MANAGE},
    "HR": {Permission.DASHBOARD_READ, Permission.USERS_MANAGE},
    "CUSTOMER_SERVICE": {Permission.DASHBOARD_READ, Permission.SALES_READ, Permission.OPERATIONS_READ, Permission.SUPPORT_READ, Permission.SUPPORT_WRITE},
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
