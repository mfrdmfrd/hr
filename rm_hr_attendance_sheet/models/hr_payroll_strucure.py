# -*- coding: utf-8 -*-


from odoo import models, fields, tools, api, exceptions, _


class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure"

    type_id = fields.Many2one(
        'hr.payroll.structure.type', required=True)
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.company.country_id)
    unpaid_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', 'hr_payroll_structure_hr_work_entry_type_rel')

    class HrPayrollStructureType(models.Model):
        _inherit = "hr.payroll.structure.type"

        wage_type = fields.Selection([('monthly', 'Monthly Fixed Wage'), ('hourly', 'Hourly Wage')], default='monthly', required=True)
