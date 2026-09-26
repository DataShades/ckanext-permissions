from __future__ import annotations

from markupsafe import escape

import ckan.plugins.toolkit as tk

from ckanext.tables.shared import FormatterResult, Options, Value, formatters


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

    The ``value`` is the display name; the link is built from the row's ``name``.
    """

    def format(self, value: Value, options: Options) -> FormatterResult:  # noqa: ARG002
        icon = tk.h.snippet("user/snippets/placeholder.html", size=20, user_name=value)
        url = tk.h.url_for("user.read", id=self.initial_row["name"])

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
