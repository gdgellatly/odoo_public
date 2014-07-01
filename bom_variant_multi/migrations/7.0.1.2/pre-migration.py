# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2013 Therp BV (<http://therp.nl>).
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


def fix_bom_templates(cr):
    """
    In OpenERP 7.0, templates have been migrated to use
    a product_id as an exemplar so we need to move
    them to be products.
    """
    openupgrade.logged_query(
        cr,
        """
        UPDATE mrp_bom m
        SET product_id = (SELECT id FROM product_product pp WHERE pp.product_tmpl_id = m.product_tmpl_id LIMIT 1)
        WHERE m.product_tmpl_id IS NOT NULL
        """)

@openupgrade.migrate()
def migrate(cr, version):
    fix_bom_templates(cr)
