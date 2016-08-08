import logging

import base64
from ast import literal_eval
import time

from openerp import exceptions
from openerp.osv import orm, fields
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class ResUsers(orm.Model):
    _inherit = 'res.users'

    _columns = {
        'oidc_provider_id': fields.many2one('auth.oidc.provider', 'OpenID Connect Provider'),
        'oidc_uid': fields.char('OpenID Connect User ID'),
        'oidc_id_token': fields.char('OpenID Connect ID Token', readonly=True),
        'oidc_object_id': fields.char('OpenID Connect Object ID'),
    }

    _sql_constraints = [
        ('uniq_users_oidc_provider_oidc_uid',
         'unique(oidc_provider_id, oidc_uid)',
         'OpenID Connect User ID must be unique per provider'),
        ('uniq_users_oidc_provider_oidc_object_id',
         'unique(oidc_provider_id, oidc_object_id)',
         'OpenID Connect Object ID must be unique per provider'),
    ]

    def _decode_code(self, code):
        segments = code.split('.')

        if (len(segments) != 3):
            raise Exception(
                'Wrong number of segments in token: %s' % code)

        hdr = segments[0].encode('ascii')
        hdr = literal_eval(
            base64.urlsafe_b64decode(hdr  + '=' * (4 - len(hdr) % 4)))

        body = segments[1].encode('ascii')
        body = literal_eval(
            base64.urlsafe_b64decode(body + '=' * (4 - len(body) % 4)))

        signature = segments[2]

        return (hdr, body, signature)

    def _auth_oidc_signin(self, cr, uid, provider, body, params, context=None):
        """ retrieve and sign in the user corresponding to provider and 
        validated access token
            :param provider: OpenID Connect provider id (int)
            :param body: result of validation of id_token (dict)
            :param params: oauth parameters (dict)
            :return: user login (str)
            :raise: openerp.exceptions.AccessDenied if signin failed

            This method can be overridden to add alternative signin methods.
        """
        oidc_uid = body['upn']
        # oidc_object_id = body['oid']
        user_ids = self.search(cr, uid, [("oidc_uid", "=", oidc_uid), ('oidc_provider_id', '=', provider)])
        if not user_ids:
            raise exceptions.AccessDenied()

        assert len(user_ids) == 1
        user = self.browse(cr, uid, user_ids[0], context=context)

        user.write({'oidc_id_token': params['id_token']})
        return user.login

    def perform_validation_checks(self, cr, uid, provider, nonce, validation, context=None):
        hdr, body, signature = validation
        provider = self.pool['auth.oidc.provider'].browse(cr, uid, provider,
                                                           context=context)
        ok = True
        if provider.client_id != body.get("aud"):
            return False
        if body.get("nonce") != nonce:
            return False
        if not body.get('oid'):
            return False
        
        now = time.time()
        if now > body.get('exp', 0.0):
            return False
        if 'nbf' in body and now < body.get('nbf'):
            return False
        return True

    def auth_oidc(self, cr, uid, provider, nonce, params, context=None):
        id_token = params.get('id_token')
        validation = self._decode_code(id_token)
        # required check
        if not self.perform_validation_checks(
                cr, uid, provider, nonce, validation, context=context):
            raise exceptions.AccessDenied()
        # retrieve and sign in user
        login = self._auth_oidc_signin(
            cr, uid, provider, validation[1], params, context=context)
        if not login:
            raise exceptions.AccessDenied()
        # return user credentials
        return (cr.dbname, login, id_token)

    def check_credentials(self, cr, uid, password):
        try:
            return super(ResUsers, self).check_credentials(cr, uid, password)
        except exceptions.AccessDenied:
            res = self.search(cr, SUPERUSER_ID, [('id', '=', uid), ('oidc_id_token', '=', password)])
            if not res:
                raise

#
