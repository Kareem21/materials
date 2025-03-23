{
    'name': 'Project Material Budget',
    'version': '18.0.1.0.0',
    'summary': 'Material Budget Control for Projects',
    'description': """
        This module provides budget control for project materials via cost sheets.
        Features:
        - Create cost sheets with budgeted quantities and costs
        - Link material requests to cost sheets
        - Get budget warnings when requests exceed budgeted amounts
    """,
    'category': 'Project',
    'author': 'Mismar',
    'website': 'https://www.mismar.ai',
    'depends': [
        'base',
        'project',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/cost_sheet_views.xml',
        'views/stock_request_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}