# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning, ValidationError
class BonusRequest(models.Model):
    _name = "bonus.request.batch"
    _inherit = "bonus.request"
    is_batch = fields.Boolean(default = True)
    department_id = fields.Many2one('hr.department')
    company_id = fields.Many2one('res.company')
    employee_ids = fields.Many2many('hr.employee',store = True,readonly = False,compute = '_set_employee_ids')
    @api.model
    def create(self, vals):
        vals['name'] = (self.env['ir.sequence'].next_by_code('bonus.request.batch')) or 'New'
        return super().create(vals)
    @api.depends('department_id','company_id')
    def _set_employee_ids(self):
        for rec in self:
            domain = []
            if rec.company_id:
                domain.append(('company_id','=',rec.company_id.id))
            if rec.department_id:
                domain.append(('department_id','=',rec.department_id.id))
            employees = self.env['hr.employee'].search(domain)
            rec.employee_ids = [(6,0,employees.ids)]
    bonus_recs = fields.One2many('bonus.request','batch_id')
    
    def generate_bonus_lines(self):
        self.bonus_recs = [(6,0,[])]
        
        default_vals = self.read()[0]
        default_vals.pop('is_batch', None)
        default_vals.pop('department_id', None)
        default_vals.pop('company_id', None)
        default_vals.pop('employee_ids', None)
        default_vals.pop('bonus_recs', None)
        default_vals.pop('name', None)

        for employee in self.employee_ids:
            emp_vals = default_vals.copy()
            emp_vals['employee_id'] = employee.id
            emp_vals['is_batch'] = False


            self.bonus_recs = [(0,0,emp_vals)]
    def approve(self):
        for rec in self:
            for bonus in rec.bonus_recs:
                bonus.approve()
            rec.state = 'confirm'
    def reject(self):
        for bonus in self.bonus_recs:
            bonus.reject()
        self.state = 'rejected'

