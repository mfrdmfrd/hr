# -*- coding: utf-8 -*-

##############################################################################
#
#
#    Copyright (C) 2020-TODAY .
#    Author: Eng.Ramadan Khalil (<rkhalil1990@gmail.com>)
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
##############################################################################

from odoo import models, fields, api, tools, _
import babel
import time
from datetime import datetime, timedelta,date
from calendar import monthrange
class HrContract(models.Model):
    _inherit = 'hr.employee.public'
    time_off_resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours', readonly=False)
class HrContract(models.Model):
    _inherit = 'hr.employee'
    time_off_resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours', readonly=False)
class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'
    att_policy_id = fields.Many2one('hr.attendance.policy',
                                    string='Attendance Policy')
    shifts_line_id = fields.Many2one('resource.calendar',string="Shifts")
    allowance_salary_structure_id = fields.Many2one('hr.payroll.structure')
    wage_type = fields.Selection(related='structure_type_id.wage_type', readonly=True)
    hourly_wage = fields.Monetary('Hourly Wage', default=0, required=True, tracking=True,
                                  help="Employee's hourly gross wage.")

    def get_days_in_month(self,current_date):
        return monthrange(current_date.year,current_date.month)[1]
