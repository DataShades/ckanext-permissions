import json
import logging
from typing import IO

import click

import ckan.plugins.toolkit as tk
from ckan import model

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


def _format_errors(error: tk.ValidationError) -> str:
    messages = []

    for value in error.error_dict.values():
        messages.extend(value if isinstance(value, list) else [value])

    return "\n".join(str(message) for message in messages)
