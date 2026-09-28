ckan.module("perm-permission-export", function ($) {
  return {
    initialize: function () {
      this.textarea = this.el.find("textarea");
      this.status = this.el.find(".perm-export-status");

      this.el.find("[data-action=copy]").on("click", this._onCopy.bind(this));
      this.el.find("[data-action=download]").on("click", this._onDownload.bind(this));
      this.el.on("hidden.bs.modal", () => this.status.empty());
    },

    _onCopy: function () {
      // The clipboard API only exists on HTTPS pages.
      const copied = navigator.clipboard ? navigator.clipboard.writeText(this.textarea.val()) : Promise.reject();

      copied.then(
        () => this.status.text(this._("Copied")),
        () => {
          this.textarea.trigger("select");
          this.status.text(this._("Press Ctrl+C to copy the selected text"));
        },
      );
    },

    _onDownload: function () {
      const link = document.createElement("a");

      link.href = URL.createObjectURL(new Blob([this.textarea.val()], { type: "application/json" }));
      link.download = `permissions-${window.location.hostname}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
    },
  };
});
