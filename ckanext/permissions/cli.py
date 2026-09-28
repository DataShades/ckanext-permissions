import logging

import click

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
