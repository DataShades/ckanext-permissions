from __future__ import annotations

from typing import Any

from markupsafe import escape

import ckan.plugins.toolkit as tk

from ckanext.tables.shared import FormatterResult, Options, Value, formatters

from ckanext.permissions.const import SCOPE_ORGANIZATION, ChangeAction
from ckanext.permissions.utils import get_permissions


class RoleLabelFormatter(formatters.BaseFormatter):
    """Render the role label, with a lock icon for the built-in roles."""

    def format(self, value: Value, options: Options) -> FormatterResult:  # noqa: ARG002
        label = escape(value)

        if not tk.h.is_default_role(self.initial_row["id"]):
            return label

        hint = escape(tk._("Built-in role, it can't be deleted"))

        return tk.literal(
            f'{label} <span class="text-muted ms-1" title="{hint}">'
            f'<i class="fa fa-lock" aria-hidden="true"></i><span class="visually-hidden">{hint}</span></span>'
        )


class UserLinkFormatter(formatters.BaseFormatter):
    """Render an avatar and a profile link for the user in the row.

    The ``value`` is the display name; the link is built from the row's ``name``,
    or the field set by the ``name_field`` option.
    """

    def format(self, value: Value, options: Options) -> FormatterResult:
        icon = tk.h.snippet("user/snippets/placeholder.html", size=20, user_name=value)
        url = tk.h.url_for("user.read", id=self.initial_row[options.get("name_field", "name")])

        return tk.literal(f'<a href="{escape(url)}">{icon} {escape(value)}</a>')


class RoleBadgesFormatter(formatters.BaseFormatter):
    """Render the row's ``role_ids`` as badges with the role labels."""

    def format(self, value: Value, options: Options) -> FormatterResult:  # noqa: ARG002
        labels = self.table.get_formatter_cache("role_labels")

        if not labels:
            labels.update(tk.h.get_registered_roles())

        badges = [
            f'<span class="badge {"bg-black" if tk.h.is_default_role(role) else "bg-success"}">'
            f"{escape(labels.get(role, role))}</span>"
            for role in self.initial_row.get("role_ids") or []
        ]

        return tk.literal(f'<div class="d-flex flex-wrap gap-1">{"".join(badges)}</div>')


class ChangeUserFormatter(UserLinkFormatter):
    """Link a user of a change; without an account, show the stored value or the ``empty`` option."""

    def format(self, value: Value, options: Options) -> FormatterResult:
        if self.initial_row.get(options["name_field"]):
            return super().format(value, options)

        return escape(value or options.get("empty", ""))


class ChangeActionFormatter(formatters.BaseFormatter):
    def format(self, value: Value, options: Options) -> FormatterResult:  # noqa: ARG002
        labels = {
            ChangeAction.RoleCreated.value: (tk._("Role created"), "bg-success"),
            ChangeAction.RoleUpdated.value: (tk._("Role updated"), "bg-primary"),
            ChangeAction.RoleDeleted.value: (tk._("Role deleted"), "bg-danger"),
            ChangeAction.PermissionGranted.value: (tk._("Permission granted"), "bg-success"),
            ChangeAction.PermissionRevoked.value: (tk._("Permission revoked"), "bg-warning text-dark"),
            ChangeAction.RoleAssigned.value: (tk._("Role assigned"), "bg-success"),
            ChangeAction.RoleUnassigned.value: (tk._("Role unassigned"), "bg-warning text-dark"),
        }
        label, badge = labels.get(value, (value, "bg-secondary"))

        return tk.literal(f'<span class="badge {badge}">{escape(label)}</span>')


class ChangeDetailsFormatter(formatters.BaseFormatter):
    """Describe a change from the row's ``data``; permission changes need no details."""

    def format(self, value: Value, options: Options) -> FormatterResult:  # noqa: ARG002
        action = self.initial_row["action"]
        data = self.initial_row.get("data") or {}

        if action == ChangeAction.RoleCreated.value:
            lines = [escape(data.get("description", ""))]
        elif action == ChangeAction.RoleUpdated.value:
            changes = data.get("changes", {})
            lines = [
                f"{escape(title)}: <del>{escape(changes[field][0])}</del> &rarr; {escape(changes[field][1])}"
                for field, title in [("label", tk._("Label")), ("description", tk._("Description"))]
                if field in changes
            ]
        elif action == ChangeAction.RoleDeleted.value:
            lines = [f"{escape(tk._('Permissions'))}: {escape(self._permission_labels(data.get('permissions', [])))}"]
        elif action in (ChangeAction.RoleAssigned.value, ChangeAction.RoleUnassigned.value):
            lines = [escape(self._scope_label(data))]
        else:
            lines = []

        return tk.literal("<br>".join(lines))

    def _scope_label(self, data: dict[str, Any]) -> str:
        if data.get("scope") != SCOPE_ORGANIZATION:
            return tk._("Global")

        return tk._("Organization: {organization}").format(organization=data.get("organization_label", ""))

    def _permission_labels(self, keys: list[str]) -> str:
        if not keys:
            return tk._("none")

        permissions = get_permissions()

        return ", ".join(permissions[key]["label"] if key in permissions else key for key in keys)
