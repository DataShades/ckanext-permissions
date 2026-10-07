import json
import logging
from datetime import datetime, timedelta, timezone
from typing import IO

import click

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.permissions import model as perm_model
from ckanext.permissions import utils

__all__ = ["permissions"]

log = logging.getLogger(__name__)


@click.group()
def permissions():
    """Permissions management commands."""


@permissions.command()
@click.option("--delete", is_flag=True, help="Delete the listed grants")
def orphans(delete: bool):
    """List role grants of permissions that no loaded permission group defines.

    These grants have no effect and can't be revoked on the permissions page.
    """
    grants = utils.get_unregistered_grants()

    if not grants:
        click.secho("No grants of undefined permissions", fg="green")
        return

    for grant in grants:
        click.echo(f"{grant.permission}\t{grant.role_id}")

    if not delete:
        click.secho(f"{len(grants)} grant(s) of undefined permissions, use --delete to remove them", fg="yellow")
        return

    revoked = [(grant.permission, grant.role_id) for grant in grants]

    for grant in grants:
        grant.delete(commit=False)

    model.Session.commit()

    for permission, role_id in revoked:
        log.info("Permission revoked: permission=%s role=%s actor=cli", permission, role_id)

    click.secho(f"{len(grants)} grant(s) deleted", fg="green")


@permissions.command("export")
@click.argument("output", type=click.File("w"), default="-")
def export_permissions(output: IO[str]):
    """Write the permissions of every role as JSON to OUTPUT, or to stdout."""
    data = tk.get_action("permissions_export")({"ignore_auth": True}, {})

    json.dump(data, output, indent=2)
    output.write("\n")


@permissions.command("import")
@click.argument("source", type=click.File("r"), default="-")
@click.option("--dry-run", is_flag=True, help="Show the changes without saving them")
def import_permissions(source: IO[str], dry_run: bool):
    """Give each role in SOURCE, or stdin, exactly the permissions listed for it.

    Roles missing from SOURCE keep their permissions.
    """
    try:
        plan = utils.plan_permissions_import(json.load(source))
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON: {e}") from e
    except tk.ValidationError as e:
        raise click.ClickException(_format_errors(e)) from e

    for role_id in plan.unknown_roles:
        click.secho(f"Skipped role {role_id}: it doesn't exist", fg="yellow")

    for permission in plan.unknown_permissions:
        click.secho(f"Skipped permission {permission}: no loaded permission group defines it", fg="yellow")

    for permission, role_id in plan.blocked:
        click.secho(f"Skipped permission {permission} for role {role_id}: the role can't be given it", fg="yellow")

    changes = plan.get_changes()

    if not changes:
        click.secho("Permissions already match", fg="green")
        return

    for permission, role_id, granted in changes:
        click.echo(f"{'+' if granted else '-'} {permission}\t{role_id}")

    if dry_run:
        click.secho(f"{len(changes)} change(s), run without --dry-run to save them", fg="yellow")
        return

    try:
        tk.get_action("permissions_update")({"ignore_auth": True}, {"permissions": plan.permissions})
    except tk.ValidationError as e:
        raise click.ClickException(_format_errors(e)) from e

    click.secho(f"{len(changes)} change(s) saved", fg="green")


@permissions.group()
def roles():
    """Role management commands."""


@roles.command("sync")
@click.option("--dry-run", is_flag=True, help="Show the changes without saving them")
def sync_roles(dry_run: bool):
    """Create the roles declared in ckanext.permissions.roles that are missing from the database.

    Warns about declared roles whose label or description differs from the database,
    and about database roles no longer declared anywhere. Neither is changed automatically.
    """
    plan = utils.plan_roles_sync()

    for drift in plan.drifted:
        click.secho(
            f"Role {drift.role_id}: declared {drift.field} ({drift.declared!r}) differs from the database "
            f"({drift.current!r}); not overwriting",
            fg="yellow",
        )

    for role in plan.undeclared:
        click.secho(
            f"Role {role.role_id} ({role.label}) is no longer declared: {role.user_count} user(s) assigned, "
            f"{role.permission_count} permission(s) granted; not deleting",
            fg="yellow",
        )

    if not plan.to_create:
        click.secho("No roles to create", fg="green")
        return

    for role in plan.to_create:
        click.echo(f"+ {role['id']}\t{role['label']}")

    if dry_run:
        click.secho(f"{len(plan.to_create)} role(s) to create, run without --dry-run to create them", fg="yellow")
        return

    try:
        for role in plan.to_create:
            tk.get_action("permission_role_create")({"ignore_auth": True}, dict(role))
    except tk.ValidationError as e:
        raise click.ClickException(_format_errors(e)) from e

    click.secho(f"{len(plan.to_create)} role(s) created", fg="green")


@permissions.group()
def changes():
    """Change log commands."""


@changes.command()
@click.option(
    "--older-than", "days", type=click.IntRange(min=1), required=True, help="Delete entries older than this many days"
)
@click.option("--dry-run", is_flag=True, help="Count the entries without deleting them")
def prune(days: int, dry_run: bool):
    """Delete change log entries older than the given number of days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = perm_model.ChangeLog.older_than(cutoff)
    count = entries.count()

    if not count:
        click.secho(f"No change log entries older than {days} day(s)", fg="green")
        return

    if dry_run:
        click.secho(f"{count} entry(ies) older than {days} day(s), run without --dry-run to delete them", fg="yellow")
        return

    entries.delete(synchronize_session=False)
    model.Session.commit()

    log.info("Change log pruned: before=%s deleted=%s actor=cli", cutoff.isoformat(), count)
    click.secho(f"{count} entry(ies) deleted", fg="green")


def _format_errors(error: tk.ValidationError) -> str:
    messages = []

    for value in error.error_dict.values():
        messages.extend(value if isinstance(value, list) else [value])

    return "\n".join(str(message) for message in messages)
