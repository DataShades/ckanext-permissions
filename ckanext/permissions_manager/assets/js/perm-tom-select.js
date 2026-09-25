ckan.module("perm-tom-select", function ($) {
    return {
        options: {
            valueField: "value",
            labelField: "text",
            plugins: {
                remove_button: {},
                dropdown_input: {},
                clear_button: {},
            },
            loadUrl: null,
            create: true,
            delimiter: ",",
        },

        initialize() {
            $.proxyAll(this, /_/);

            if (typeof TomSelect === "undefined") {
                console.error("[bulk-tom-select] TomSelect library is not loaded");
                return
            }

            this.options.plugins.remove_button.title = this._("Remove this item");
            this.options.plugins.clear_button.title = this._("Remove all selected options");

            if (this.options.loadUrl) {
                this.options.load = this._loadOptions;
            }

            if (this.el.get(0, {}).tomselect) {
                return;
            }

            this.widget = new TomSelect(this.el, this.options);
        },

        _loadOptions: function (query, callback) {
            var self = this;

            if (self.loading > 1) {
                callback();
                return;
            }

            fetch(this.options.loadUrl)
                .then(response => response.json())
                .then(json => {
                    callback(json.result);
                    self.settings.load = null;
                }).catch(() => {
                    callback();
                });

        },
    };
});
