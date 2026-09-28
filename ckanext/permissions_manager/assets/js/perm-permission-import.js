ckan.module("perm-permission-import", function ($) {
  return {
    options: {
      target: null,
      version: null,
      roles: {},
      permissions: [],
    },

    initialize: function () {
      this.form = $("#" + this.options.target);
      this.textarea = this.el.find("textarea");
      this.error = this.el.find(".perm-import-error");
      this.notice = this.form.find(".perm-import-notice");

      this.el.find("input[type=file]").on("change", this._onFile.bind(this));
      this.el.find("[data-action=apply]").on("click", this._onApply.bind(this));
      this.el.on("hidden.bs.modal", () => this._showError(""));
      this.form.on("reset", () => this.notice.addClass("d-none").empty());
    },

    _onFile: function (event) {
      const input = event.target;
      const file = input.files[0];

      if (!file) {
        return;
      }

      file.text().then((text) => {
        this.textarea.val(text);
        this._showError("");
        input.value = "";
      });
    },

    _onApply: function () {
      let data;

      try {
        data = JSON.parse(this.textarea.val());
      } catch (e) {
        this._showError(this._("Invalid JSON: %(error)s", { error: e.message }));
        return;
      }

      const error = this._validate(data);

      if (error) {
        this._showError(error);
        return;
      }

      this._announce(this._apply(data.roles));
      this.form.trigger("perm-matrix:refresh");
      this.textarea.val("");
      this.el.modal("hide");
    },

    _validate: function (data) {
      if (!$.isPlainObject(data)) {
        return this._("The export must be a JSON object");
      }

      if (data.version !== this.options.version) {
        return this._("Unsupported export version %(version)s, expected %(expected)s", {
          version: data.version,
          expected: this.options.version,
        });
      }

      const valid =
        $.isPlainObject(data.roles) &&
        Object.values(data.roles).every(
          (granted) => Array.isArray(granted) && granted.every((permission) => typeof permission === "string"),
        );

      return valid ? null : this._("The export must map each role to a list of permissions");
    },

    _apply: function (roles) {
      const checkboxes = this.form.find("input[type=checkbox][data-permission]");
      const result = { applied: [], unknownRoles: [], unknownPermissions: new Set(), blocked: [] };

      Object.entries(roles).forEach(([role, granted]) => {
        granted
          .filter((permission) => !this.options.permissions.includes(permission))
          .forEach((permission) => result.unknownPermissions.add(permission));

        if (!(role in this.options.roles)) {
          result.unknownRoles.push(role);
          return;
        }

        const roleCheckboxes = checkboxes.filter((_, el) => el.dataset.role === role);
        const available = roleCheckboxes.map((_, el) => el.dataset.permission).get();

        granted
          .filter((permission) => this.options.permissions.includes(permission) && !available.includes(permission))
          .forEach((permission) => result.blocked.push(`${permission} (${this.options.roles[role]})`));

        roleCheckboxes.each((_, el) => {
          el.checked = granted.includes(el.dataset.permission);
        });

        result.applied.push(this.options.roles[role]);
      });

      return result;
    },

    _announce: function (result) {
      const messages = [
        result.applied.length
          ? this._("Imported the permissions of %(roles)s. Review the highlighted changes and save them.", {
              roles: result.applied.join(", "),
            })
          : this._("None of the imported roles exist on this portal."),
      ];

      if (result.unknownRoles.length) {
        messages.push(this._("Skipped roles that don't exist: %(roles)s", { roles: result.unknownRoles.join(", ") }));
      }

      if (result.unknownPermissions.size) {
        messages.push(
          this._("Skipped permissions that no permission group defines: %(permissions)s", {
            permissions: [...result.unknownPermissions].join(", "),
          }),
        );
      }

      if (result.blocked.length) {
        messages.push(
          this._("Skipped permissions the role can't be given: %(permissions)s", {
            permissions: result.blocked.join(", "),
          }),
        );
      }

      const skipped = messages.length > 1 || !result.applied.length;

      this.notice
        .empty()
        .append(messages.map((message) => $("<p>").addClass("mb-0").text(message)))
        .toggleClass("alert-info", !skipped)
        .toggleClass("alert-warning", skipped)
        .removeClass("d-none");
    },

    _showError: function (message) {
      this.error.text(message).toggleClass("d-none", !message);
    },
  };
});
