ckan.module("perm-confirm-role-removal", function ($) {
  return {
    options: {
      role: null,
      message: null,
    },

    initialize: function () {
      this.select = this.el.find("select[name=roles]");
      this.hadRole = this._hasRole();
      this.el.on("submit", this._onSubmit.bind(this));
    },

    _hasRole: function () {
      return (this.select.val() || []).includes(this.options.role);
    },

    _onSubmit: function (event) {
      if (!this.hadRole || this._hasRole()) {
        return;
      }

      event.preventDefault();

      ckan.confirm({
        message: this.options.message,
        onConfirm: () => this.el.get(0).submit(),
      });
    },
  };
});
