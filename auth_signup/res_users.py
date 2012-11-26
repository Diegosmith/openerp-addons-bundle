# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
import random
import time
import urllib
import urlparse

from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.safe_eval import safe_eval

class SignupError(Exception):
    pass

def random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.choice(chars) for _ in xrange(20))

def now():
    return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

class res_partner(osv.Model):
    _inherit = 'res.partner'

    def _get_signup_valid(self, cr, uid, ids, name, arg, context=None):
        dt = now()
        res = {}
        for partner in self.browse(cr, uid, ids, context):
            res[partner.id] = bool(partner.signup_token) and \
                                (not partner.signup_expiration or dt <= partner.signup_expiration)
        return res

    def _get_signup_url_for_action(self, cr, uid, ids, action='login', view_type=None, menu_id=None, res_id=None, context=None):
        """ generate a signup url for the given partner ids and action, possibly overriding
            the url state components (menu_id, id, view_type) """
        res = dict.fromkeys(ids, False)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for partner in self.browse(cr, uid, ids, context):
            # when required, make sure the partner has a valid signup token
            if context and context.get('signup_valid') and not partner.user_ids:
                self.signup_prepare(cr, uid, [partner.id], context=context)
    
            action_template = None
            params = {
                'action': urllib.quote(action),
                'db': urllib.quote(cr.dbname),
            }
            if partner.signup_token:
                action_template = "?db=%(db)s#action=%(action)s&token=%(token)s"
                params['token'] = urllib.quote(partner.signup_token)
            elif partner.user_ids:
                action_template = "?db=%(db)s#action=%(action)s&db=%(db)s&login=%(login)s"
                params['login'] = urllib.quote(partner.user_ids[0].login)
            if action_template:
                if view_type:
                    action_template += '&view_type=%s' % urllib.quote(view_type)
                if menu_id:
                    action_template += '&menu_id=%s' % urllib.quote(str(menu_id))
                if res_id:
                    action_template += '&id=%s' % urllib.quote(str(res_id))
                res[partner.id] = urlparse.urljoin(base_url, action_template % params)
        return res

    def _get_signup_url(self, cr, uid, ids, name, arg, context=None):
        """ proxy for function field towards actual implementation """
        return self._get_signup_url_for_action(cr, uid, ids, context=context)

    _columns = {
        'signup_token': fields.char('Signup Token'),
        'signup_expiration': fields.datetime('Signup Expiration'),
        'signup_valid': fields.function(_get_signup_valid, type='boolean', string='Signup Token is Valid'),
        'signup_url': fields.function(_get_signup_url, type='char', string='Signup URL'),
    }

    def action_signup_prepare(self, cr, uid, ids, context=None):
        return self.signup_prepare(cr, uid, ids, context=context)

    def signup_prepare(self, cr, uid, ids, expiration=False, context=None):
        """ generate a new token for the partners with the given validity, if necessary
            :param expiration: the expiration datetime of the token (string, optional)
        """
        for partner in self.browse(cr, uid, ids, context):
            if expiration or not partner.signup_valid:
                token = random_token()
                while self._signup_retrieve_partner(cr, uid, token, context=context):
                    token = random_token()
                partner.write({'signup_token': token, 'signup_expiration': expiration})
        return True

    def _signup_retrieve_partner(self, cr, uid, token,
            check_validity=False, raise_exception=False, context=None):
        """ find the partner corresponding to a token, and possibly check its validity
            :param token: the token to resolve
            :param check_validity: if True, also check validity
            :param raise_exception: if True, raise exception instead of returning False
            :return: partner (browse record) or False (if raise_exception is False)
        """
        partner_ids = self.search(cr, uid, [('signup_token', '=', token)], context=context)
        if not partner_ids:
            if raise_exception:
                raise SignupError("Signup token '%s' is not valid" % token)
            return False
        partner = self.browse(cr, uid, partner_ids[0], context)
        if check_validity and not partner.signup_valid:
            if raise_exception:
                raise SignupError("Signup token '%s' is no longer valid" % token)
            return False
        return partner

    def signup_retrieve_info(self, cr, uid, token, context=None):
        """ retrieve the user info about the token
            :return: a dictionary with the user information:
                - 'db': the name of the database
                - 'token': the token, if token is valid
                - 'name': the name of the partner, if token is valid
                - 'login': the user login, if the user already exists
                - 'email': the partner email, if the user does not exist
        """
        partner = self._signup_retrieve_partner(cr, uid, token, raise_exception=True, context=None)
        res = {'db': cr.dbname}
        if partner.signup_valid:
            res['token'] = token
            res['name'] = partner.name
        if partner.user_ids:
            res['login'] = partner.user_ids[0].login
        else:
            res['email'] = partner.email or ''
        return res

class res_users(osv.Model):
    _inherit = 'res.users'

    def _get_state(self, cr, uid, ids, name, arg, context=None):
        return dict((user.id, 'new' if not user.login_date else 'reset' if user.signup_token else 'active')
                    for user in self.browse(cr, uid, ids, context))

    _columns = {
        'state': fields.function(_get_state, string='Status', type='selection',
                    selection=[('new', 'New'), ('active', 'Active'), ('reset', 'Resetting Password')]),
    }

    def signup(self, cr, uid, values, token=None, context=None):
        """ signup a user, to either:
            - create a new user (no token), or
            - create a user for a partner (with token, but no user for partner), or
            - change the password of a user (with token, and existing user).
            :param values: a dictionary with field values that are written on user
            :param token: signup token (optional)
            :return: (dbname, login, password) for the signed up user
        """
        if token:
            # signup with a token: find the corresponding partner id
            res_partner = self.pool.get('res.partner')
            partner = res_partner._signup_retrieve_partner(
                            cr, uid, token, check_validity=True, raise_exception=True, context=None)
            # invalidate signup token
            partner.write({'signup_token': False, 'signup_expiration': False})

            partner_user = partner.user_ids and partner.user_ids[0] or False
            if partner_user:
                # user exists, modify it according to values
                values.pop('login', None)
                values.pop('name', None)
                partner_user.write(values)
                return (cr.dbname, partner_user.login, values.get('password'))
            else:
                # user does not exist: sign up invited user
                values.update({
                    'name': partner.name,
                    'partner_id': partner.id,
                    'email': values.get('email') or values.get('login'),
                })
                self._signup_create_user(cr, uid, values, context=context)
        else:
            # no token, sign up an external user
            values['email'] = values.get('email') or values.get('login')
            self._signup_create_user(cr, uid, values, context=context)

        return (cr.dbname, values.get('login'), values.get('password'))

    def _signup_create_user(self, cr, uid, values, context=None):
        """ create a new user from the template user """
        ir_config_parameter = self.pool.get('ir.config_parameter')
        template_user_id = safe_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.template_user_id', 'False'))
        assert template_user_id and self.exists(cr, uid, template_user_id, context=context), 'Signup: invalid template user'

        # check that uninvited users may sign up
        if 'partner_id' not in values:
            if not safe_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.allow_uninvited', 'False')):
                raise SignupError('Signup is not allowed for uninvited users')

        assert values.get('login'), "Signup: no login given for new user"
        assert values.get('partner_id') or values.get('name'), "Signup: no name or partner given for new user"

        # create a copy of the template user (attached to a specific partner_id if given)
        values['active'] = True
        return self.copy(cr, uid, template_user_id, values, context=context)
