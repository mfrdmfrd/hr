# -*- coding: utf-8 -*-


from odoo import models, fields, tools, api, exceptions, _


class HrWorkEntry(models.Model):
    _inherit = "hr.work.entry.type"

    round_days = fields.Selection(
        [('NO', 'No Rounding'),
         ('HALF', 'Half Day'),
         ('FULL', 'Day')
        ], string="Rounding", required=True, default='NO',
        help="When the work entry is displayed in the payslip, the value is rounded accordingly.")
    round_days_type = fields.Selection(
        [('HALF-UP', 'Closest'),
         ('UP', 'Up'),
         ('DOWN', 'Down')
        ], string="Round Type", required=True, default='DOWN',
        help="Way of rounding the work entry type.")
