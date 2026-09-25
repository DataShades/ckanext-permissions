import click

from ckan import model

import ckanext.permissions.const as perm_const
from ckanext.permissions import model as perm_model
from ckanext.permissions import utils

__all__ = ["permissions"]


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
@click.argument("role", default=perm_const.Roles.Authenticated.value, required=False)
@click.option(
    "--user-ids",
    "-u",
    multiple=True,
    help="User IDs to remove role from (if not specified, removes from all users)",
)
def remove_role_from_users(role: str, user_ids: tuple[str, ...]):
    """Remove automatic roles from users."""
    users = model.Session.query(model.User).filter(model.User.id.in_(user_ids)).all() if user_ids else model.User.all()

    for user in users:
        utils.remove_role_from_user(user.id, role)

    if user_ids:
        click.secho(f"Role '{role}' removed from {len(users)} specified user(s)", fg="green")
    else:
        click.secho(f"Role '{role}' removed from all users", fg="green")
