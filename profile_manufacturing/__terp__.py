# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
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


{
    'name': 'Manufacturing industry profile',
    'version': '1.0',
    'category': 'Profile',
    'description': """Profile for manufacturing industries""",
    'author': 'Tiny',
    'depends': ['mrp', 'sale', 'delivery', 'board_manufacturing', 'product_margin', 'sale_delivery_report'],
    'update_xml': ['security/ir.model.access.csv', 'profile_manufacturing.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0027737506213',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
