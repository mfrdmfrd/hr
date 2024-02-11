# -*- coding: utf-8 -*-
{
    'name': "HR Attendance Sheet And Policies",

    'summary': """Managing  Attendance Sheets for Employees
        """,
    'description': """
        Employees Attendance Sheet Management   
    """,
    'author': "Ramadan Khalil",
    'website': "rkhalil1990@gmail.com",
    'price': 99,
    'currency': 'EUR',

    'category': 'hr',
    'version': '17.0.1.0',
    'images': ['static/description/bannar.jpg'],

    'depends': ['base',
                'hr',
                'hr_payroll_community',
                'hr_holidays',
                'bonus_request',
                'hr_attendance',
                'penalty_request',
                'hr_custom',#hr_custom for resg date
                'hr_work_entry',
                'hr_work_entry_contract',

                ],
    'data': [
        'data/ir_sequence.xml',
        'data/data.xml',
        'data/attendance_data2.xml',
        'data/emails.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/change_att_data_view.xml',
        'views/hr_attendance_sheet_view.xml',
        'views/hr_attendance_policy_view.xml',
        'views/hr_contract_view.xml',
        'views/hr_public_holiday_view.xml',
        'views/attendance_sheet_batch_view.xml',
        'views/payslip.xml',

    ],

    'license': 'OPL-1',
    'demo': [
        'demo/demo.xml',
    ],
}