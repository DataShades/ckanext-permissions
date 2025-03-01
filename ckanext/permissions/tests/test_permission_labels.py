from typing import Any, Callable

import pytest

import ckan.plugins.toolkit as tk
from ckan.tests.helpers import call_action


@pytest.mark.usefixtures("with_plugins", "clean_index", "clean_db")
class TestPermissionLabels:
    def test_private_dataset_is_not_visible_to_anonymous_user(
        self, app, dataset_factory: Callable[..., dict[str, Any]]
    ):
        dataset = dataset_factory(private=True)

        app.get(tk.h.url_for("dataset.read", id=dataset["id"]), headers={}, status=404)

    def test_private_dataset_make_anon_user_to_read_private_dataset(
        self, app, dataset_factory: Callable[..., dict[str, Any]]
    ):
        dataset = dataset_factory(private=True)

        call_action(
            "permissions_update",
            permissions={"read_private_dataset": {"anonymous": True}},
        )

        app.get(tk.h.url_for("dataset.read", id=dataset["id"]), headers={}, status=200)
