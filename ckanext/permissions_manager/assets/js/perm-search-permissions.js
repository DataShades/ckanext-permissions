ckan.module("perm-search-permissions", function ($, _) {
  return {
    options: {
      targetTable: null,
    },
    initialize: function () {
      const input = this.el;
      const table = $("#" + this.options.targetTable);
      const groups = table.find("tr.perm-group-row");
      const permissions = table.find("tr.perm-permission-row");
      const noResults = table.find("tr.perm-no-results");
      const clearBtn = $("#clear-search");

      const filter = function (query) {
        let anyVisible = false;

        groups.each(function () {
          const group = $(this);
          const groupMatch = group.text().toLowerCase().includes(query);
          const members = permissions.filter((_, row) => row.dataset.group === group.data("group").toString());
          let memberVisible = false;

          members.each(function () {
            const visible = groupMatch || this.dataset.search.toLowerCase().includes(query);

            $(this).toggle(visible);
            memberVisible = memberVisible || visible;
          });

          group.toggle(groupMatch || memberVisible);
          anyVisible = anyVisible || groupMatch || memberVisible;
        });

        noResults.toggleClass("d-none", anyVisible);
      };

      input.on("input", function () {
        const query = $(this).val().toLowerCase().trim();

        clearBtn.prop("disabled", !query);
        filter(query);
      });

      clearBtn.on("click", function () {
        input.val("");
        clearBtn.prop("disabled", true);
        filter("");
      });
    },
  };
});
