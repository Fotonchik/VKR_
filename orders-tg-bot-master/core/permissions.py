# core/permissions.py

ROLE_PRIORITY = {
    "admin": 3,
    "manager": 2,
    "operator": 1,
    "client": 0
}


class PermissionError(Exception):
    pass


def has_role(user_role: str, required_role: str) -> bool:
    return ROLE_PRIORITY.get(user_role, -1) >= ROLE_PRIORITY.get(required_role, 0)


def require_role(user_role: str, required_role: str):
    if not has_role(user_role, required_role):
        raise PermissionError(
            f"Недостаточно прав: требуется {required_role}, текущая роль {user_role}"
        )

# =========================================================
# BASIC CHECKS
# =========================================================

def is_admin(role: str) -> bool:
    return role == "admin"


def is_manager(role: str) -> bool:
    return role == "manager"


def is_operator(role: str) -> bool:
    return role == "operator"


def is_staff(role: str) -> bool:
    return role in ("admin", "manager", "operator")


# =========================================================
# STAFF MANAGEMENT
# =========================================================

def can_manage_staff(role: str) -> bool:
    return role in ("admin", "manager")


def can_manage_role(current_role: str, target_role: str) -> bool:
    """
    Можно ли назначать / менять роль
    """
    if current_role == "admin":
        return True

    if current_role == "manager":
        return target_role in ("manager", "operator")

    return False


def get_visible_roles(role: str):
    if role == "admin":
        return ["admin", "manager", "operator"]

    if role == "manager":
        return ["manager", "operator"]

    return []


# =========================================================
# SAFETY
# =========================================================

def can_delete_user(current_user_id: int, target_user_id: int) -> bool:
    """
    Нельзя удалить или деактивировать себя
    """
    return current_user_id != target_user_id


def can_edit_user(current_user_role: str, target_role: str) -> bool:
    """
    Нельзя редактировать пользователя с ролью выше
    """
    return ROLE_PRIORITY[current_user_role] > ROLE_PRIORITY[target_role]


# =========================================================
# TICKETS
# =========================================================

def can_view_ticket(current_role: str, ticket_owner_id: int, user_id: int) -> bool:
    if is_staff(current_role):
        return True
    return ticket_owner_id == user_id


def can_change_ticket_status(current_role: str) -> bool:
    return current_role in ("admin", "manager", "operator")