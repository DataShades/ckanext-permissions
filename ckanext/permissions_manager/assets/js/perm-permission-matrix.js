ckan.module("perm-permission-matrix", function ($) {
  return {
    initialize: function () {
      this.checkboxes = this.el.find("input[type=checkbox][data-permission]");
      this.counter = this.el.find(".perm-unsaved-count");
      this.buttons = this.el.find(".perm-matrix-actions button");
      this.submitting = false;

      this.checkboxes.on("change", this._update.bind(this));
      this.el.on("reset", () => setTimeout(this._update.bind(this)));
      this.el.on("submit", () => (this.submitting = true));
      $(window).on("beforeunload", this._onBeforeUnload.bind(this));

      this._restoreSubmitted();
      this._update();
    },

    _restoreSubmitted: function () {
      this.checkboxes.filter("[data-submitted]").each((_, el) => {
        el.checked = el.dataset.submitted === "true";
      });
    },

    _changed: function () {
      return this.checkboxes.filter((_, el) => el.checked !== el.defaultChecked);
    },

    _update: function () {
      const count = this._changed().length;

      this.checkboxes.each((_, el) => {
        $(el).closest("td").toggleClass("perm-changed", el.checked !== el.defaultChecked);
      });

      this.counter.text(count ? this.ngettext("%(num)d unsaved change", "%(num)d unsaved changes", count) : "");
      this.buttons.prop("disabled", !count);
    },

    _onBeforeUnload: function (event) {
      if (this.submitting || !this._changed().length) {
        return;
      }

      event.preventDefault();
      event.returnValue = "";
    },
  };
});
