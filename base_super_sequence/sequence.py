# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP / Odoo, Open Source Management Solution - module extension
#    Copyright (C) 2014- O4SB (<http://openforsmallbusiness.co.nz>).
#    Author Graeme Gellatly <g@o4sb.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm, fields


class SuperSequence(orm.Model):
    """Super Sequence"""
    _name = 'super.sequence'
    _description = __doc__

    columns = {'%s_increment' % f: fields.integer(string='%s' % f) for f in
               ('sale, out, in, mrp, purchase, '
                'out_invoice, out_refund, in_invoice, in_refund')}

    _columns = dict({'linked_doc_ids': fields.one2many(
        'linked.document', 'seq_id', string='Linked Documents',
        auto_join=True)}, columns)

    _defaults = {'%s_increment' % f: 0 for f in
                 ('sale, out, in, mrp, purchase, '
                  'out_invoice, out_refund, in_invoice, in_refund')}
