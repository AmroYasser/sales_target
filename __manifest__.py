{
    'name': "Sales Target",
    'author': "Amr Yasser",
    'depends': ['base', 'point_of_sale', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/sales_target_view.xml',
    ],
    'installable': True,
    'application': True,
}