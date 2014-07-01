# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution - module extension
#    Copyright (C) 2010- Graeme Gellatly - O4SB (<http://openforsmallbusiness.co.nz>).
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from datetime import date
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from tools import DEFAULT_SERVER_DATE_FORMAT

from report import report_sxw
import pooler

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.init_bal_sum = 0.0
        self.total = []
        self.headings = []
        self.headings = self._headings()
        self.localcontext.update( {
            'adr_get': self._adr_get,
#            'lines': self._lines,
            'total': self._get_total,
            'initial': self._get_initial,
            'total_heading': self._get_headings,
            'calc_totals': self._get_balance_data,
            'invoices': self._get_invoices,
            'payments': self._get_payments,
        })
        
    def _get_balance_data(self, partner):
        self.total = [0.0, 0.0, 0.0, 0.0, 0.0]
        cr, uid = self.cr, self.uid
        db_pool = pooler.get_pool(cr.dbname)   
        data = self.localcontext['form']
        
        pb_obj = db_pool.get('end_period.balance')
        search_args = [('partner_id', '=', partner.id),
                       ('period_id.date_stop', '=', data['period_from'])]
        if data['multicompany']:
            bal_uid = 1
        else:
            bal_uid = uid
            search_args.append(('company_id', '=', data['company_id']))
        pb_ids = pb_obj.search(cr, bal_uid, search_args)
        if pb_ids:
            for period_balances in pb_obj.browse(cr, uid, pb_ids):
                self.total[1] += period_balances.p1
                self.total[2] += period_balances.p2
                self.total[3] += period_balances.p3
                self.total[4] += period_balances.opening
                self.init_bal_sum += period_balances.opening
        return True
    
    def _get_total(self, key):
        """
        Returns float value of list at position key
        @param key: an int
        """ 
        return self.total[key]
   
    def _get_initial(self):
        """
        @return: float initial balance
        """
        return self.init_bal_sum
    
    def _headings(self):
        """
        @return: a list of headings for aging
        """
        if self.localcontext['form']['aging'] == 'months':
            return ['Current', '1 Month', '2 Month', '3 Months +', 'Total']
        else:
            days = self.localcontext['form']['days']
            return [('0-'+str(days)+' days'), (str(days+1)+'-'+str(days*2)+' days'), str(days*2+1)+'-'+str(days*3)+' days', str(days*3+1)+' days+', 'Total']
 
    def _get_headings(self, key):
        """
        @return: value of list at position key
        @param key: an int
        """ 
        return self.headings[key]
  
    def _adr_get(self, partner, type):
        """
        @return: a res.partner.address browse record of partner and type
        @param partner: usually latest partner browse record - 'o'
        @param type: the type of address e.g. 'invoice' 
        """
        cr, uid = self.cr, self.uid
        db_pool = pooler.get_pool(cr.dbname)
        res_partner = db_pool.get('res.partner')
        res_partner_address = []
        if partner.address:
            addresses = res_partner.address_get(cr, uid, [partner.id], [type])
            if addresses:
                res_partner_address = db_pool.get('res.partner.address').browse(
                                                            cr, uid, [addresses[type]])
        return res_partner_address
        
    def _get_invoices(self, partner):
        cr, uid = self.cr, self.uid
        db_pool = pooler.get_pool(cr.dbname)   
        data = self.localcontext['form']
        inv_obj = db_pool.get('account.invoice')
        search_args = [('partner_id', '=', partner.id),
                       ('type', 'ilike', 'out_'),
                       ('period_id.date_stop', '=', data['period_from']),
                       ('state', 'not in', ('draft', 'cancel'))]
        if data['multicompany']:
            bal_uid = 1
        else:
            bal_uid = uid
            search_args.append(('company_id', '=', data['company_id']))
        inv_ids = inv_obj.search(cr, bal_uid, search_args)
        res = []        
        for inv in inv_obj.browse(cr, bal_uid, inv_ids):
            site = inv.order_ids and inv.order_ids[0].drop_ship and inv.order_ids[0] or False
            if site:
                site = '%s %s' % (site.ship_to_name, site.ship_to_address_id.name)            
            res.append({
                        'name':inv.number,
                        'description': inv.name,
                        'site': site,
                        'type': inv.type == 'out_invoice' and 'Invoice' or 'Credit Note',
                        'amount_original': inv.type == 'out_invoice' and inv.amount_total or -inv.amount_total,
                        'date_original': inv.date_invoice,
                        'amount_unreconciled': inv.type == 'out_invoice' and inv.residual or -inv.residual,
                        })
            self.total[0] += res[-1]['amount_unreconciled']
            self.total[4] += res[-1]['amount_original']
        return sorted(res, key=itemgetter('name'))
    
    def _get_payments(self, partner):
        cr, uid = self.cr, self.uid
        db_pool = pooler.get_pool(cr.dbname)   
        data = self.localcontext['form']
        search_args = [('period_id.date_stop', '=', data['period_from']),
                       ('partner_id', '=', partner.id),
                       ('journal_id.type', '=', 'bank'),
                       ('credit', '=', 0.0),
                       ('account_id.type', 'not in', ['receivable', 'payable'])]
        if data['multicompany']:
            bal_uid = 1
        else:
            bal_uid = uid
            search_args.append(('company_id', '=', data['company_id']))
        move_obj = db_pool.get('account.move.line')
        move_ids = move_obj.search(cr, bal_uid, search_args)
        res = []
        payment = 0.0
        unrec_payment = 0.0
        for line in move_obj.browse(cr, bal_uid, move_ids):
            res.append({
                'name':line.move_id.name,
                'description': line.ref,
                'type': line.credit and 'dr' or 'cr',
                'amount_original': line.credit and line.credit or line.debit * -1,
                'date_original':line.date,
                'amount_unreconciled': line.credit and line.amount_residual_currency * -1 or line.amount_residual_currency,
                })
            self.total[0] += res[-1]['amount_unreconciled']
            self.total[4] += res[-1]['amount_original']
        return sorted(res, key=itemgetter('name'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
