# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2013 Sylvain LE GAL
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

from openerp.openupgrade import openupgrade

column_renames = {
    'stock_inventory_line': [('price_unit', None)],
    'stock_production_lot': [('last_cost', None)]
}

def migrate_cost_methods(cr):
    cr.execute('''UPDATE product_template SET cost_method = 'average' WHERE cost_method = 'lot';''')


@openupgrade.migrate()
def migrate(cr, version):
    openupgrade.delete_model_workflow(cr, 'edi.invoice.o4sb')
    openupgrade.rename_columns(cr, column_renames)
    migrate_cost_methods(cr)
