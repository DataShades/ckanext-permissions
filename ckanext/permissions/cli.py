import logging

import click

from ckan import model

import ckanext.permissions.const as perm_const
from ckanext.permissions import model as perm_model
from ckanext.permissions import utils

__all__ = ["permissions"]

log = logging.getLogger(__name__)


@click.group()
def permissions():
    """Permissions management commands."""


@permissions.command()
def init_default_roles():
    """Create default roles (anonymous, authenticated, administrator) in the database."""
    created_count = utils.ensure_default_roles()

    if created_count > 0:
        click.secho(f"{created_count} role(s) created successfully", fg="green")
    else:
        click.secho("All default roles already exist", fg="yellow")

    return created_count


@permissions.command()
@click.argument("role", default=perm_const.Roles.Authenticated.value, required=False)
def assign_default_user_roles(role: str):
    """Assign automatic roles to users (initializes default roles if needed)."""
    # Ensure default roles exist
    click.echo("Checking default roles...")
    created_count = utils.ensure_default_roles()

    if created_count > 0:
        click.secho(f"{created_count} role(s) created", fg="green")
        click.echo()  # Empty line for readability

    # Check if the specified role exists
    if not perm_model.Role.get(role):
        click.secho(f"Error: Role '{role}' does not exist", fg="red")
        return

    users = model.Session.query(model.User).filter(model.User.state == "active").all()

    for user in users:
        utils.assign_role_to_user(user.id, role)

    click.secho(f"Role '{role}' assigned to {len(users)} active user(s)", fg="green")


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
