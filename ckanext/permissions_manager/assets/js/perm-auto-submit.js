ckan.module("perm-auto-submit", function ($) {
  return {
    initialize: function () {
      this.el.on("change", () => this.el.get(0).form.requestSubmit());
    },
  };
});
