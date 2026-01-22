[![Tests](https://github.com/DataShades/ckanext-permissions/actions/workflows/test.yml/badge.svg)](https://github.com/DataShades/ckanext-permissions/actions/workflows/test.yml)

# ckanext-permissions

> [!WARNING]
> This extension is still under development and not ready for production use.

The extension allows you to build a Access Control List (ACL) system within CKAN.

![acl.png](doc/acl.png)


### Roles

The extension has a 3 default roles: `anonymous`, `authenticated` and `administrator`. And allows you to define custom roles.

![roles.png](doc/roles.png)

### Assigning roles to users

The extension provides a way to assign roles to users. Roles could be global and scoped to an organization.

![role-assignment.png](doc/role-assignment.png)


## Requirements

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.9 and earlier | no            |
| 2.10+           | yes           |
| 2.11+           | yes           |


## Installation

Using GIT Clone:

1. Activate your CKAN virtual environment, for example:
   ```bash
   . /usr/lib/ckan/default/bin/activate
   ```

2. Clone the source and install it on the virtualenv:
   ```bash
   git clone https://github.com/DataShades/ckanext-permissions.git
   cd ckanext-permissions
   pip install -e .
   ```

3. Add `permissions permissions_manager` to the `ckan.plugins` setting in your CKAN config file (by default the config file is located at `/etc/ckan/default/ckan.ini`).

4. Initialize DB tables:
   ```bash
   ckan -c /etc/ckan/default/ckan.ini db upgrade -p permissions
   ```

5. Initialize default Roles and add Authenticated default role to all existing Users:
   ```bash
   ckan -c /etc/ckan/default/ckan.ini permissions assign-default-user-roles
   ```

6. Restart CKAN. For example:
   ```bash
   sudo supervisorctl restart ckan-uwsgi
   ```


## Config settings

TBD


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini --cov=ckanext.permissions


## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
