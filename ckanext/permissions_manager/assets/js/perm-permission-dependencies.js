ckan.module("perm-permission-dependencies", function ($) {
  return {
    initialize: function () {
      this.checkboxes = this.el.find("input[type=checkbox][data-permission]");
      this.checkboxes.on("change", this._onChange.bind(this));
    },

    _onChange: function (event) {
      const checkbox = event.target;
      const role = checkbox.dataset.role;

      if (checkbox.checked) {
        this._dependsOn(checkbox).forEach((dependency) => this._set(dependency, role, true));
        return;
      }

      this.checkboxes
        .filter((_, el) => el.dataset.role === role && this._dependsOn(el).includes(checkbox.dataset.permission))
        .each((_, el) => this._set(el.dataset.permission, role, false));
    },

    _dependsOn: function (checkbox) {
      return (checkbox.dataset.dependsOn || "").split(" ").filter(Boolean);
    },

    _set: function (permission, role, checked) {
      const target = this.checkboxes.filter(
        (_, el) => el.dataset.permission === permission && el.dataset.role === role,
      );

      if (target.length && target.prop("checked") !== checked) {
        target.prop("checked", checked).trigger("change");
      }
    },
  };
});
