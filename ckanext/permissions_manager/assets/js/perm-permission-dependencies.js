ckan.module("perm-permission-dependencies", function ($) {
  return {
    initialize: function () {
      this.checkboxes = this.el.find("input[type=checkbox][data-permission]");
      this.notice = this.el.closest("form").find(".perm-cascade-notice");
      this.cascading = false;

      this.checkboxes.on("change", this._onChange.bind(this));
      this.el.closest("form").on("reset", () => this.notice.addClass("d-none").empty());
    },

    _onChange: function (event) {
      if (this.cascading) {
        return;
      }

      const checkbox = event.target;
      const changed = [];

      this._propagate(checkbox, changed);

      this.cascading = true;
      changed.forEach((el) => $(el).trigger("change"));
      this.cascading = false;

      changed.forEach((el) => this._highlight(el));
      this._announce(checkbox, changed);
    },

    _propagate: function (checkbox, changed) {
      const role = checkbox.dataset.role;
      const targets = checkbox.checked
        ? this._dependsOn(checkbox).map((permission) => this._find(permission, role))
        : this.checkboxes
            .filter((_, el) => el.dataset.role === role && this._dependsOn(el).includes(checkbox.dataset.permission))
            .toArray();

      targets.forEach((el) => {
        if (!el || el.checked === checkbox.checked) {
          return;
        }

        el.checked = checkbox.checked;
        changed.push(el);
        this._propagate(el, changed);
      });
    },

    _dependsOn: function (checkbox) {
      return (checkbox.dataset.dependsOn || "").split(" ").filter(Boolean);
    },

    _find: function (permission, role) {
      return this.checkboxes
        .filter((_, el) => el.dataset.permission === permission && el.dataset.role === role)
        .get(0);
    },

    _highlight: function (el) {
      const cell = $(el).closest("td");

      cell.removeClass("perm-cascaded");
      void cell.get(0).offsetWidth;
      cell.addClass("perm-cascaded");
    },

    _announce: function (checkbox, changed) {
      if (!changed.length) {
        this.notice.addClass("d-none").empty();
        return;
      }

      const params = {
        role: checkbox.dataset.roleLabel,
        permissions: changed.map((el) => el.dataset.permissionLabel).join(", "),
      };
      const message = checkbox.checked
        ? this._("Also granted to %(role)s: %(permissions)s", params)
        : this._("Also revoked from %(role)s: %(permissions)s", params);

      this.notice.text(message).removeClass("d-none");
    },
  };
});
