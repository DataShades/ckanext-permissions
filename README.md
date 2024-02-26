[![Tests](https://github.com/mutantsan/ckanext-permissions/actions/workflows/test.yml/badge.svg)](https://github.com/mutantsan/ckanext-permissions/actions/workflows/test.yml)

# ckanext-permissions

The extension allows you to build a permission system within CKAN. For now, it uses
3 default roles: anonymous, user and sysadmin. We plan to expand the functionallity to
allow registering context roles, like organisation `admin`, `editor` or `member`.

Or even create a custom role and assign it to user to apply specific checks. For example,
create a role `moderator` and allow those users to delete `comments` in `ckanext-comments`
extension.

This feature is experimental. For now it requires alteration in CKAN core to work.

```diff
    diff --git a/ckan/logic/__init__.py b/ckan/logic/__init__.py
    index 18ccd59e4..62da81720 100644
    --- a/ckan/logic/__init__.py
    +++ b/ckan/logic/__init__.py
    @@ -365,6 +365,10 @@ def check_access(action: str,
            authorized to call the named action

        '''
    +    from ckanext.permissions.utils import check_access as perm_check_access
    +
    +    if perm_check_access(action, context, data_dict):
    +        return True

        # Auth Auditing.  We remove this call from the __auth_audit stack to show
        # we have called the auth function
```

## Requirements

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.7 and earlier | no            |
| 2.8             | no            |
| 2.9             | no            |
| 2.10+           | yes           |


## Installation

Install it from `pypi` (TBD) or from source if you know what you are doing. Refer to CKAN
[documentation](https://docs.ckan.org/en/latest/extensions/tutorial.html#installing-the-extension) to know, how to install extension from source.


## Config settings

TBD


## Tests

We have tests so if you are changing something, ensure that they are not broken. To run the tests, do:

    pytest --ckan-ini=test.ini


## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
