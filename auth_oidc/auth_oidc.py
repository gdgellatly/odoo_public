from openerp.osv import orm, fields

class AuthOidcProvider(orm.Model):
    """'OpenID Connect provider'"""

    _name = 'auth.oidc.provider'
    _description = __doc__
    _order = 'name'

    _columns = {
        'name' : fields.char('Provider name'),               # Name of the OpenID Connect entity
        'client_id' : fields.char('Client ID'),              # Our identifier
        'auth_endpoint' : fields.char('Authentication URL'), # OAuth provider URL to authenticate users
        'body': fields.char('Body'),
        'enabled' : fields.boolean('Allowed'),
        'css_class' : fields.char('CSS class'),
        'sequence' : fields.integer(),
    }
    _defaults = {
        'enabled': False,
        'css_class': "zocial",
    }
