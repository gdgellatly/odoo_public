class account_report_partner_statement(osv.osv_memory): 
    _name = 'account.partner.statement'
    _description = 'Statement of Account'
    
    _columns = {
        'initial_balance': fields.boolean('Include initial balances',
                                    help='It adds initial balance row on report which display previous sum amount of debit/credit/balance'),
        'reconcil': fields.boolean('Include Reconciled Entries', help='Consider reconciled entries'),
        'partners': fields.many2many('res.partner', 'custom_report_partner_rel', 'partners', 'partner_id', 'Partners', required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'chart_account_id': fields.many2one('account.account', 'Chart of account', help='Select Charts of Accounts', required=True, domain = [('parent_id','=',False)]),
        'period_from': fields.many2one('account.period', 'Period'),
        'statement_type': fields.selection([('open', 'Open Item'), ('activity', 'Activity')],"Statement Type", required=True),
        'result_selection': fields.selection([('receivable','Receivable Accounts'),
                                              ('payable','Payable Accounts'),
                                              ('customer_supplier','Receivable and Payable Accounts')],
                                              "Partner Types", required=True),
        'zero_balance': fields.boolean('Include Zero balances'),
        'aging': fields.selection([('months', 'Age by Months'),('days', 'Age by Days')], 'Aging', help='Show aging on balances by days or months'),
        'days': fields.integer('Days'),
        'date_from': fields.date('Date From'),
        'target_move': fields.selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),
                                        ], 'Target Moves', required=True),
        'groupdebtor': fields.boolean('Central Debtor', help='If partner is a parent include subsidiaries activity'),
        'multicompany': fields.boolean('Consolidated Statement', help='Consolidated Statement from this and all child companies - requires appropriate access rights')
    }

### Functions to initialise defaults    
    def _get_company_id(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr,uid, uid).company_id.id
        return company or False

    def _get_period(self, cr, uid, context=None):
        last_month = (datetime.now()-relativedelta(months=1)).strftime('%Y-%m-%d')
        company_id = self._get_company_id(cr, uid, context)      
        period = self.pool.get('account.period').search(cr, uid, [('date_start', '<', last_month), ('date_stop', '>', last_month), ('company_id', '=', company_id)] ,)
        return period and period[0] or False

    def _get_account(self, cr, uid, context=None):
        company_id = self._get_company_id(cr, uid, context)
        accounts = self.pool.get('account.account').search(cr, uid, [('parent_id', '=', False), ('company_id', '=', company_id)], limit=1)
        return accounts and accounts[0] or False
    
    def _get_default_partners(self, cr, uid, context=None):
        if context['active_model'] == 'res.partner':
            return self.pool.get('res.partner').search(cr, uid, [('id', 'in', context['active_ids'])], context=context)
        return False

    _defaults = {
        'company_id': _get_company_id,
        'period_from': _get_period,
        'statement_type': 'open',
        'result_selection': 'receivable',
        'reconcil': False,
        'zero_balance': False,
        'initial_balance': False,
        'multicompany': False,
        'groupdebtor': False,
        'aging': 'months',
        'days': 30,
        'partners': _get_default_partners,
        'target_move': 'posted',
    }

### Onchange Functions to set logical default settings for changes    
    def onchange_aging(self, cr, uid, ids, aging, company_id, context=None):
        res = {}
        if not company_id:
            return res
        last_month = (datetime.now()-relativedelta(months=1)).strftime('%Y-%m-%d')
        if aging == 'days':
            res['value'] = {'period_from': False, 'date_from': time.strftime('%Y-01-01')}
        if aging == 'months':
            period = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', last_month), ('date_stop', '>=', last_month), ('company_id', '=', company_id)] ,)
            res['value'] = {'period_from': period[0], 'date_from': False}
        return res
    
    def onchange_statement_type(self, cr, uid, ids, statement_type, context=None):
        if statement_type == 'open':
            return {'value': {'initial_balance': False, 'reconcil': False}}
        return {'value': {'initial_balance': True, 'reconcil': True}}

### Functions for check_report to generate non partner dependent info to report to reduce processing time    
    def _get_date(self, cr, uid, ids, context):
        """Determines date report is based on, 
        @return: iso_format/postgres formatted date string"""
        fields = self.read(cr, uid, ids, ['aging', 'date_from', 'period_from'], context)[0] 
        if fields['aging'] == 'months':
            period = self.pool.get('account.period').browse(cr, uid, fields['period_from'][0])
            return period.date_stop
        else: 
            return fields['date_from']
        
    def _move_ids(self, cr, uid, ids, context=None):
        """
        @return: dictionary whose keys are partner ids, and values are lists
        of move line ids relevant to the partner and wizard input
        """
        move_line_pool = self.pool.get('account.move.line')
        fields = self.read(cr,uid,ids,['groupdebtor', 'partners', 'target_move', 'result_selection', 'reconcil', 'company_id', 'multicompany'], context=context)[0]
        query = False
        cr.execute('''SELECT l.id
                    FROM account_move_line l,
                    LEFT JOIN account_move am ON am.id = l.move_id
                    WHERE l.partner_id IN (%s) AND
                            am.state IN (%s) AND
                            ''')
        move_state = ['draft','posted']
        if fields['target_move'] == 'posted':
            move_state = ['posted']
        search_tuples = [('move_id.state', 'in', move_state)]
        
        partner_ids = fields['partners']
        if fields['groupdebtor']:
            search_tuples.extend(['|',('partner_id.parent_id', '!=', False),('partner_id', 'in', partner_ids)])
        else:
            search_tuples.append(('partner_id', 'in', partner_ids))
# We have a limitation here.  If we use the commented out search tuple, lines reconciled after NOW (as in the 
# date the report is run, will still show the reconciled amount.  While this can be tested, if it was previously 
# partially reconciled, OpenERP does not store this information, so either way it would be wrong.  With the current
# implementation, entries reconciled as of NOW will not show.  This is acceptable, because, even if the counter
# reconciling entry occurred after the date of the report, in most cases it also would be reconciled.  This limitation
# is primarily only felt in monthly aging reports, as in days aging NOW and date can be the same        
        if not fields['reconcil']:
            search_tuples.append(('reconcile_id', '=', False))
#            search_tuples.extend(['|',('reconcile_id', '=', False), ('reconcile_id.create_date', '>', self._get_date(cr, uid, ids, context))])
        
        if fields['result_selection'] == 'customer_supplier':
            search_tuples.append(('account_id.type', 'in', ['receivable', 'payable']))
        else: 
            search_tuples.append(('account_id.type', '=', fields['result_selection']))
        
        company_ids = [fields['company_id'][0]]
        if fields['multicompany']:
            company_pool_obj = self.pool.get('res.company')
            company_ids.extend([x[0] for x in company_pool_obj.search(cr, uid, [('id', 'child_of', company_ids)] )])
        search_tuples.append(('company_id', 'in', company_ids))
        
        ids = move_line_pool.search(cr, uid, search_tuples)
        ids.reverse()
        move_lines = move_line_pool.browse(cr, uid, ids, context)
        res = dict((partner_id, []) for partner_id in partner_ids)
        for line in move_lines:
            if line.partner_id.id in partner_ids:
                res[line.partner_id.id].append(line.id) 
            if fields['groupdebtor']:
                if line.partner_id.parent_id and (line.partner_id.parent_id.id in partner_ids):
                    res[line.partner_id.parent_id.id].append(line.id)
                if line.partner_id.parent_id.parent_id and (line.partner_id.parent_id.parent_id.id in partner_ids):
                    res[line.partner_id.parent_id.parent_id.id].append(line.id)      
        return res
    
    def _get_partners(self, cr, uid, ids, move_ids, context=None): 
        """
        @param move_ids: a dictionary with key partner_id, and a list of move_ids           
        @return: a list of ints (partner_ids) ordered alphabetically
        """ 
        def _check_lines(cr, uid, ids, partner_id, move_ids, context):
            """ 
            @param partner_id: takes a partner_id 
            @return: True if there are associated move_ids, otherwise False
            """
            if partner_id in move_ids and move_ids[partner_id]:
                return True
            return False
        
        partner_obj = self.pool.get('res.partner')
        fields = self.read(cr, uid, ids, ['partners', 'zero_balance', 'result_selection'], context=context)[0]
        partner_ids = fields['partners']
        res_partners = partner_obj.browse(cr, uid, partner_ids, context)
        if not fields['zero_balance']:
            partner_ids = [partner.id for partner in res_partners if _check_lines(cr, uid, ids, partner.id, move_ids, context)]
            res_partners = partner_obj.browse(cr, uid, partner_ids, context=context)
        if fields['result_selection'] == 'receivable':
            partner_ids = [partner.id for partner in res_partners if partner.customer]
        elif fields['result_selection'] == 'payable':
            partner_ids = [partner.id for partner in res_partners if partner.supplier]
        elif fields['result_selection'] == 'customer_supplier':
            partner_ids = [partner.id for partner in res_partners]
        partner_ids = [x['id'] for x in sorted(partner_obj.read(cr, uid, partner_ids, ['id', 'name']), key=itemgetter('name'))]
        return partner_ids

### Function to prepare data for sending to report
    def check_report(self, cr, uid, ids, context=None):
        """
        Prepares data for sending to parser.
        @return: report object res.partner.statement
        """
        if context is None:
            context = {}
        data = {}
        data['move_ids'] = self._move_ids(cr, uid, ids, context)
        data['ids'] = self._get_partners(cr, uid, ids, data['move_ids'], context)
        data['id'] = data['ids'][0]
        data['date'] = self._get_date(cr, uid, ids, context)
        data['model'] = context.get('active_model', 'res.partner')
        data['form'] = self.read(cr, uid, ids, ['initial_balance', 'statement_type', 'aging', 'days', 
                                                'company_id', 'groupdebtor', 'multicompany'], context=context)[0]
        context.update(data)
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'res.partner.statement',
            'datas': data,
            'context': context,
            }