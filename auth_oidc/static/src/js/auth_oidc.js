openerp.auth_oidc = function(instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.web.Login.include({
        start: function(parent, params) {
            var self = this;
            var d = this._super.apply(this, arguments);
            this.$el.hide();
            this.$el.on('click', 'a.zocial', this.on_oidc_sign_in);
            this.oidc_providers = [];
            if(this.params.oidc_error === 1) {
                this.do_warn(_t("Sign up error"),_t("Sign up is not allowed on this database."), true);
            } else if(this.params.oidc_error === 2) {
                this.do_warn(_t("Authentication error"),_t("Access Denied"), true);
            } else if(this.params.oidc_error === 3) {
                this.do_warn(_t("Authentication error"),_t("You do not have access to this database or your invitation has expired. Please ask for an invitation and be sure to follow the link in your invitation email."), true);
            }
            return d.done(this.do_oidc_load).fail(function() {
                self.do_oidc_load([]);
            });
        },
        on_db_loaded: function(result) {
            this._super.apply(this, arguments);
            this.$("form [name=db]").change(this.do_oidc_load);
        },
        do_oidc_load: function() {
            var db = this.$("form [name=db]").val();
            if (db) {
                this.rpc("/auth_oidc/list_providers", { dbname: db }).done(this.on_oidc_loaded);
            } else {
                this.$el.show();
            }
        },
        on_oidc_loaded: function(result) {
            this.oidc_providers = result;
            var params = $.deparam($.param.querystring());
            if (this.oidc_providers.length === 1 && params.type === 'signup') {
                this.do_oidc_sign_in(this.oidc_providers[0]);
            } else {
                this.$el.show();
                this.$('.oe_oidc_provider_login_button').remove();
                var buttons = QWeb.render("auth_oidc.Login.button",{"widget":this});
                this.$(".oe_login_pane form ul").after(buttons);
            }
        },
        on_oidc_sign_in: function(ev) {
            ev.preventDefault();
            var index = $(ev.target).data('index');
            var provider = this.oidc_providers[index];
            return this.do_oidc_sign_in(provider);
        },
        do_oidc_sign_in: function(provider) {
            var return_url = _.str.sprintf('%s//%s/auth_oidc/signin', location.protocol, location.host);
            if (instance.session.debug) {
                return_url += '?debug';
            }
            var state = this._oidc_state(provider);
            var nonce = this._make_nonce(24);
            state.n = nonce;
            var params = {
                response_type: 'id_token',
                client_id: provider.client_id,
                redirect_uri: return_url,
                nonce: nonce,
                state: JSON.stringify(state),
            };
            var url = provider.auth_endpoint + '?' + $.param(params);
            instance.web.redirect(url);
        },
        _oidc_state: function(provider) {
            // return the state object sent back with the redirected uri
            var dbname = this.$("form [name=db]").val();
            return {
                d: dbname,
                p: provider.id,
            };
        },
        _make_nonce: function(length) {
            var text = "";
            var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
            for(var i = 0; i < length; i++) {
                text += possible.charAt(Math.floor(Math.random() * possible.length));
            }
            return text;
        },
    });

};
