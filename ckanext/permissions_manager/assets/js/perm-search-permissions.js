ckan.module("perm-search-permissions", function ($, _) {
  return {
    options: {
      targetTable: null,
    },
    initialize: function () {
      const input = this.el;
      const tableId = this.options.targetTable;
      const table = $("#" + tableId);
      const rows = table.find("tbody tr");
      const clearBtn = $("#clear-search");

      input.on("input", function () {
        const filter = $(this).val().toLowerCase();

        clearBtn.prop("disabled", !filter.trim());

        rows.each(function () {
          const text = $(this).text().toLowerCase();
          $(this).toggle(text.includes(filter));
        });
      });

      clearBtn.on("click", function () {
        input.val("");
        clearBtn.prop("disabled", true);

        rows.show();
      });
    },
  };
});
