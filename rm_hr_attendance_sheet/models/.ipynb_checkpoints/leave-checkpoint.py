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


import pytz
from operator import itemgetter
from odoo import api, fields, models, _
from datetime import datetime,time
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
class ResourceCalendar(models.Model):
    _inherit = "hr.leave.type"
    
    is_deduct = fields.Boolean()
    is_deduct_day = fields.Boolean()
    is_deduct_half_day = fields.Boolean()


    is_mission = fields.Boolean()
    is_sick = fields.Boolean()
    is_deduct_leave = fields.Boolean()
    is_pregnancy = fields.Boolean()
    is_work_injury = fields.Boolean()
    is_permission = fields.Boolean()
    is_weekend_included = fields.Boolean()
    
class ResourceCalendar(models.Model):
    _inherit = "hr.leave"
    allocations_left = fields.Float(compute = '_set_allocations_left')
    @api.depends('employee_id','employee_id','holiday_status_id','request_date_from')
    def _set_allocations_left(self):
        for rec in self:
            if not((rec.employee_id or len(rec.employee_ids)) and rec.holiday_status_id and rec.request_date_from):
                rec.allocations_left = 0
                continue
            today = fields.Date.today()
            employee = rec.employee_id 
            if not(employee):
                employee = rec.employee_ids[0]
            allocations = self.env['hr.leave.allocation'].sudo().search([('employee_id','=',employee.id),('holiday_status_id','=',rec.holiday_status_id.id),('date_from','<=',rec.request_date_from)])
            rec.allocations_left = sum([allocation.max_leaves - allocation.leaves_taken for allocation in allocations])
    def refuse_multi(self):
        for rec in self:
            if rec.state in ['confirm','validate1','validate']:
                rec.action_refuse()
    def draft_multi(self):
        for rec in self:
            if rec.state in ['confirm','refuse']:
                rec.action_draft()
    def confirm_multi(self):
        for rec in self:
            if rec.state in ['draft']:
                rec.action_confirm()
    def approve_multi(self):
        for rec in self:
            if rec.state in ['confirm']:
                rec.action_approve()
    def validate_multi(self):
        for rec in self:
            if rec.state in ['validate1']:
                rec.action_validate()
    def _get_calendar(self):
        self.ensure_one()
        return (self.employee_id.time_off_resource_calendar_id or self.env.company.resource_calendar_id) if self.holiday_status_id.is_weekend_included else self.env.company.resource_calendar_id

#     def _get_number_of_days(self, date_from, date_to, employee_id):
#         """ Returns a float equals to the timedelta between two dates given as string."""
#         if not(self.holiday_status_id.is_weekend_included):
#             return super()._get_number_of_days(date_from, date_to, employee_id)
#         if employee_id:
#             employee = self.env['hr.employee'].browse(employee_id)
#             result = employee._get_work_days_data_batch(date_from, date_to,
#                                                         calendar=self._get_calendar())[
#                 employee.id]
#             if self.request_unit_half and result['hours'] > 0:
#                 result['days'] = 0.5
#             if not self.request_unit_hours:
#                 days = (date_to - date_from).days + 1
#                 hours = days * 8
#                 result = {'days': days, 'hours': hours}
#             return result
#         calendar = self._get_calendar()

#         today_hours = calendar.get_work_hours_count(
#             datetime.combine(date_from.date(), time.min),
#             datetime.combine(date_from.date(), time.max),
#             False)
#         hours = calendar.get_work_hours_count(date_from, date_to)
#         days = hours / (today_hours or HOURS_PER_DAY) if not self.request_unit_half else 0.5

#         test = {'days': days, 'hours': hours}
#         return test
    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Returns a float equals to the timedelta between two dates given as string."""
        
        if employee_id:
            
            if not(self.holiday_status_id.is_weekend_included):
                return super()._get_number_of_days(date_from, date_to, employee_id)
            employee = self.env['hr.employee'].browse(employee_id)
            
            # We force the company in the domain as we are more than likely in a compute_sudo
            domain = [('company_id', 'in', self.env.company.ids + self.env.context.get('allowed_company_ids', []))]
            result = employee._get_work_days_data_batch(date_from, date_to, domain=domain,calendar=self._get_calendar())[employee.id]
            if self.request_unit_half and result['hours'] > 0:
                result['days'] = 0.5
            return result
        calendar = self._get_calendar()
        
        today_hours = calendar.get_work_hours_count(
            datetime.combine(date_from.date(), time.min),
            datetime.combine(date_from.date(), time.max),
            False)

        hours = calendar.get_work_hours_count(date_from, date_to)
        days = hours / (today_hours or HOURS_PER_DAY) if not self.request_unit_half else 0.5
        return {'days': days, 'hours': hours}