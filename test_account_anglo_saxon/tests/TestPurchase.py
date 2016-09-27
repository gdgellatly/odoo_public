# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP / Odoo, Open Source Management Solution - module extension
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

from hypothesis import given
from hypothesis import strategies as st
from openerp.tests.common import SingleTransactionCase, TransactionCase
from openerp import netsvc
from openerp.tools.float_utils import float_round as round


class TestPurchase(TransactionCase):
    def __init__(self, methodName='runTest'):
        super(TestPurchase, self).__init__(methodName)

    def setUp(self):
        """Initial Setup"""
        super(TestPurchase, self).setUp()
        cr, uid = self.cr, self.uid
        self.purch_obj = self.registry('purchase.order')
        self.rcv_goods = self.registry('stock.picking.in')
        self.journal_entries = self.registry('account.move')
        self.inv_obj = self.registry('account.invoice')

        partner = self.browse_ref('base.res_partner_1')
        self.stock_account = self.ref('account.stk')
        self.stock_input_account = self.ref(
            'test_account_anglo_saxon.stk_input')
        self.payables_account = int(partner.property_account_payable.id)

        self.purchase_defaults = {
            'partner_id': partner.id,
            'warehouse_id': self.ref('stock.warehouse0'),
            'location_id': self.ref('stock.stock_location_stock'),
            'pricelist_id': self.ref('purchase.list0')
        }

        self.today = fields.date.today()
        self.validate = netsvc.LocalService("workflow").trg_validate

    def _create_and_confirm_purchase(self, line_vals, po_type='order'):
        cr, uid = self.cr, self.uid
        purchase_id = self.purch_obj.create(
            cr, uid, dict(self.purchase_defaults, **{
                'invoice_method': po_type,
                'order_line': [(0, 0, line) for line in line_vals]}))
        self.validate(uid, 'purchase.order', purchase_id,
                      'purchase_confirm', cr)
        return purchase_id

    def _get_picking(self, purchase_id):
        cr, uid = self.cr, self.uid
        picking_id = self.rcv_goods.search(cr, uid,
            [('purchase_id', '=', purchase_id)])
        self.assertTrue(len(picking_id) == 1, "No picking for purchase order")
        return self.rcv_goods.browse(cr, uid, picking_id[0])

    def _get_partial_data(self, picking):
        return {
            'move%s' % m.id: {
                'product_id': m.product_id.id,
                'product_qty': m.product_qty,
                'product_uom': m.product_uom.id,
                'product_price': m.price_unit,
                'prodlot_id': False} for m in picking.move_lines
            if m.state not in ('done', 'cancel')}

    def _get_journal_entry(self, picking):
        cr, uid = self.cr, self.uid
        journal_entry = self.journal_entries.search(cr, uid, [
            ('ref', '=', picking.name)])
        self.assertTrue(journal_entry, "Where's my journal?")
        return self.journal_entries.browse(cr, uid, journal_entry[-1])

    def _01_receive(self, purchase_id, journal_total, test_args):
        cr, uid = self.cr, self.uid

        picking = self._get_picking(purchase_id)
        partial_data = self._get_partial_data(picking)
        self.rcv_goods.do_partial(cr, uid, [picking.id], partial_data, {})
        journal_entry = self._get_journal_entry(picking)
        self.assertEqual(len(journal_entry.line_id), 2)
        expected_moves = set([(self.stock_input_account, 0.0, journal_total),
                              (self.stock_account, journal_total, 0.0)])
        actual_moves = set([(int(line.account_id.id), line.debit, line.credit) for line
                    in journal_entry.line_id])
        self.assertEqual(actual_moves, expected_moves, 'Test Args: %s' % str(test_args))

    def _01_invoice(self, purchase_id, journal_total, test_args, from_picking=False):
        cr, uid = self.cr, self.uid
        if from_picking:
            invoice_ids = self.rcv_goods.action_invoice_create(
                cr, uid, [self._get_picking(purchase_id).id],
                type='in_invoice', context={}).values()
        else:
            invoice_ids = [i.id for i in self.purch_obj.browse(
                cr, uid, purchase_id).invoice_ids]
        self.assertTrue(len(invoice_ids) == 1)
        self.validate(uid, 'account.invoice', invoice_ids[0], 'invoice_open',
                                cr)
        journal_entry = self.inv_obj.browse(cr, uid, invoice_ids[0]).move_id
        # There may be taxes so we ignore these
        expected_moves = set([(self.payables_account, 0.0, journal_total),
                              (self.stock_input_account, journal_total, 0.0)])
        actual_moves = set([(int(line.account_id.id), line.debit, line.credit) for line
                             in journal_entry.line_id])
        self.assertEqual(actual_moves, expected_moves, 'Test Args: %s' % str(test_args))

    @given(st.floats(min_value=0, max_value=1000000.0, allow_nan=False, allow_infinity=False),
           st.integers(min_value=1, max_value=1000000))
    def test_01a_receive_po_for_consu_line_order_method(self, price, qty):
        """
        We test that receiving goods from a PO for a consumable item and
        then creating an invoice creates expected journal entries when
        invoice method is order
        :param price:
        :param qty:
        :return:
        """
        price, qty = round(price, 2), float(qty)
        journal_total = round(price * qty, 2)
        line_vals = [{
            'product_id': self.ref(
                'test_account_anglo_saxon.product_product_tas_1'),
            'name': 'Test Line1',
            'price_unit': price,
            'product_qty': qty,
            'date_planned': self.today
        }]
        purchase_id = self._create_and_confirm_purchase(line_vals)
        self._01_receive(purchase_id, journal_total, (price, qty))
        self._01_invoice(purchase_id, journal_total, (price, qty))

    @given(st.floats(min_value=0, max_value=1000000.0, allow_nan=False,
                     allow_infinity=False),
           st.integers(min_value=1, max_value=1000000))
    def test_01b_receive_po_for_stock_line_picking_method(self, price, qty):
        """
        We test that receiving goods from a PO for a stock item and
        then creating an invoice creates expected journal entries when
        invoice method is picking
        :param price:
        :param qty:
        :return:
        """
        price, qty = round(price, 2), float(qty)
        journal_total = round(price * qty, 2)
        line_vals = [{
            'product_id': self.ref(
                'test_account_anglo_saxon.product_product_tas_2'),
            'name': 'Test Line2',
            'price_unit': price,
            'product_qty': qty,
            'date_planned': self.today
        }]
        purchase_id = self._create_and_confirm_purchase(line_vals, 'picking')
        self._01_receive(purchase_id, journal_total, (price, qty))
        self._01_invoice(purchase_id, journal_total, (price, qty), 'picking')

    @given(st.floats(min_value=0, max_value=1000000.0, allow_nan=False,
                     allow_infinity=False),
           st.integers(min_value=1, max_value=1000000))
    def test_03_create_invoice_receive_goods(self, price, qty):
        """
        We test that invoicing goods from a PO for a stock item and
        then receiving them creates expected journal entries when
        invoice method is order
        :param price:
        :param qty:
        :return:
        """
        price, qty = round(price, 2), float(qty)
        journal_total = round(price * qty, 2)
        line_vals = [{
            'product_id': self.ref(
                'test_account_anglo_saxon.product_product_tas_1'),
            'name': 'Test Line1',
            'price_unit': price,
            'product_qty': qty,
            'date_planned': self.today
        }]
        purchase_id = self._create_and_confirm_purchase(line_vals)
        self._01_invoice(purchase_id, journal_total, (price, qty))
        self._01_receive(purchase_id, journal_total, (price, qty))


    def test_04a_po_for_service_line_order(self):
        """
        We test that invoicing goods from a PO for a service item
        creates expected journal entries when invoice method is order
        :param price:
        :param qty:
        :return:
        """
        pass

    def test_04a_po_for_service_line_picking_method(self):
        """
        We test that invoicing goods from a PO for a service item and
        creates expected journal entries when invoice method is picking
        and does not create a picking
        :param price:
        :param qty:
        :return:
        """
        pass

    def test_01c_receive_po_for_service_line_order_method(self):
        pass