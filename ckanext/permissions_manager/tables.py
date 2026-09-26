from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import aggregate_order_by

import ckan.plugins.toolkit as tk
from ckan import model

import ckanext.tables.shared as t

from ckanext.permissions import const as perm_const
from ckanext.permissions import model as perm_model
from ckanext.permissions_manager import formatters as pf


def flatten_errors(errors: Any) -> list[str]:
    if isinstance(errors, dict):
        return [message for value in errors.values() for message in flatten_errors(value)]

    if isinstance(errors, list):
        return [message for value in errors for message in flatten_errors(value)]

    return [str(errors)]


def _count_by_role(column: Any) -> Any:
    role_id = column.class_.role_id

    return (
        sa.select(sa.func.count(sa.distinct(column)))
        .where(role_id == perm_model.Role.id)
        .correlate(perm_model.Role)
        .scalar_subquery()
    )


class RolesTable(t.TableDefinition):
    def __init__(self) -> None:
        role = perm_model.Role
        stmt = sa.select(
            role.id,
            role.label,
            role.description,
            _count_by_role(perm_model.UserRole.user_id).label("users"),
            _count_by_role(perm_model.RolePermission.permission).label("permissions"),
        ).order_by(sa.func.lower(role.label))

        super().__init__(
            name="perm_roles",
            table_template="perm_manager/role_list.html",
            data_source=t.DatabaseDataSource(stmt=stmt),
            columns=[
                t.ColumnDefinition(
                    field="label",
                    title=tk._("Label"),
                    formatters=[(pf.RoleLabelFormatter, {})],
                    tabulator_formatter="html",
                    width=160,
                ),
                t.ColumnDefinition(field="id", title=tk._("ID"), width=130),
                t.ColumnDefinition(field="description", title=tk._("Description"), min_width=300, tooltip=True),
                t.ColumnDefinition(field="users", title=tk._("Users"), width=130),
                t.ColumnDefinition(field="permissions", title=tk._("Permissions"), width=160),
            ],
            row_actions=[
                t.RowActionDefinition(
                    action="edit",
                    label=tk._("Edit"),
                    icon="fa fa-edit",
                    callback=lambda row: t.ActionHandlerResult(
                        success=True,
                        redirect=tk.url_for("perm_manager.role_edit", role_id=row["id"]),
                    ),
                ),
                t.RowActionDefinition(
                    action="delete",
                    label=tk._("Delete"),
                    icon="fa fa-trash",
                    attrs={"class": "text-danger"},
                    callback=self.delete_role,
                    with_confirmation=True,
                ),
            ],
            bulk_actions=[
                t.BulkActionDefinition(
                    action="delete",
                    label=tk._("Delete selected roles"),
                    icon="fa fa-trash",
                    attrs={"class": "text-danger"},
                    callback=self.delete_roles,
                ),
            ],
            table_actions=[
                t.TableActionDefinition(
                    action="add",
                    label=tk._("Add a new role"),
                    icon="fa fa-plus",
                    callback=lambda: t.ActionHandlerResult(success=True, redirect=tk.url_for("perm_manager.role_add")),
                    with_confirmation=False,
                ),
            ],
        )

    def delete_role(self, row: t.Row) -> t.ActionHandlerResult:
        return self.delete_roles([row])

    def delete_roles(self, rows: list[t.Row]) -> t.ActionHandlerResult:
        """Delete the roles one by one; a failed role doesn't stop the rest."""
        errors = []

        for row in rows:
            try:
                tk.get_action("permission_role_delete")({}, {"id": row["id"]})
            except tk.ValidationError as e:  # noqa: PERF203 - per-row errors are the point
                errors.extend(f"{row['id']}: {message}" for message in flatten_errors(e.error_dict))

        if errors:
            return t.ActionHandlerResult(success=False, error="; ".join(errors))

        return t.ActionHandlerResult(
            success=True,
            message=tk.ungettext("Role has been deleted", "Roles have been deleted", len(rows)),
        )


class UserRolesTable(t.TableDefinition):
    """Active users with their roles in the global scope."""

    scope = perm_const.SCOPE_GLOBAL

    def __init__(self, scope_id: str | None = None, show_all: bool = False, ajax_url: str | None = None) -> None:
        self.scope_id = scope_id
        self.show_all = show_all

        super().__init__(
            name="perm_user_roles",
            table_template="perm_manager/user_roles_list.html",
            data_source=t.DatabaseDataSource(stmt=self._get_stmt()),
            ajax_url=ajax_url,
            placeholder=tk._("No users match your filters."),
            columns=[
                t.ColumnDefinition(
                    field="display_name",
                    title=tk._("User"),
                    formatters=[(pf.UserLinkFormatter, {})],
                    tabulator_formatter="html",
                ),
                t.ColumnDefinition(
                    field="roles",
                    title=tk._("Roles"),
                    formatters=[(pf.RoleBadgesFormatter, {})],
                    tabulator_formatter="html",
                ),
            ],
            row_actions=[
                t.RowActionDefinition(
                    action="edit",
                    label=tk._("Edit roles"),
                    icon="fa fa-edit",
                    callback=lambda row: t.ActionHandlerResult(success=True, redirect=self.edit_url(row["id"])),
                ),
            ],
        )

    def edit_url(self, user_id: str) -> str:
        return tk.url_for("perm_manager.edit_user_role", user_id=user_id)

    def _get_stmt(self) -> sa.Select:
        user = model.User
        user_role = perm_model.UserRole
        role = perm_model.Role

        display_name = sa.case((sa.func.trim(user.fullname) != "", user.fullname), else_=user.name)
        user_roles = sa.and_(user_role.user_id == user.id, user_role.scope == self.scope)

        if self.scope_id:
            user_roles = sa.and_(user_roles, user_role.scope_id == self.scope_id)

        def _aggregate(value: Any) -> Any:
            return (
                sa.select(value)
                .select_from(user_role)
                .join(role, role.id == user_role.role_id)
                .where(user_roles)
                .scalar_subquery()
            )

        stmt = sa.select(
            user.id,
            user.name,
            display_name.label("display_name"),
            _aggregate(sa.func.string_agg(role.label, aggregate_order_by(sa.literal_column("', '"), role.label))).label(
                "roles"
            ),
            _aggregate(sa.func.array_agg(aggregate_order_by(user_role.role_id, role.label))).label("role_ids"),
        ).where(user.state == model.State.ACTIVE, sa.func.trim(user.email) != "")

        if self.scope_id and not self.show_all:
            is_member = sa.exists().where(
                model.Member.table_id == user.id,
                model.Member.table_name == "user",
                model.Member.group_id == self.scope_id,
                model.Member.state == model.State.ACTIVE,
            )
            stmt = stmt.where(sa.or_(is_member, sa.exists().where(user_roles)))

        return stmt.order_by(sa.func.lower(display_name), user.name)


class OrganizationUserRolesTable(UserRolesTable):
    """Users with their roles scoped to one organization.

    By default only the organization members and users that already have a
    role in it are listed; ``show_all`` lists every active user.
    """

    scope = perm_const.SCOPE_ORGANIZATION

    def __init__(self, group_dict: dict[str, Any], show_all: bool = False) -> None:
        self.group_dict = group_dict

        super().__init__(
            scope_id=group_dict["id"],
            show_all=show_all,
            ajax_url=tk.url_for(
                "perm_manager.organization_user_roles_list",
                org_id=group_dict["name"],
                all=1 if show_all else None,
            ),
        )
        self.table_template = "perm_manager/organization/user_roles_list.html"

    def edit_url(self, user_id: str) -> str:
        return tk.url_for("perm_manager.organization_edit_user_role", org_id=self.group_dict["name"], user_id=user_id)
