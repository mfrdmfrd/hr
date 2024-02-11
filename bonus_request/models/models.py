# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class hr_custom_2(models.Model):
    _inherit = 'hr.contract'
    commission_wage = fields.Float('راتب عمولة')
    commission_wage_manu = fields.Float('راتب حافز الانتاج')
    
class BonusRequest(models.Model):
    _name = "bonus.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    is_batch = fields.Boolean(default = False)
    name = fields.Char(string="Name", default="New", readonly=True, copy=False)

    state = fields.Selection(string="", selection=[('draft', 'Draft'),
                                                   ('confirm', 'Confirmed'), ('rejected', 'Rejected')], required=False, default='draft')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if not(res.is_batch):
            res.name = (self.env['ir.sequence'].next_by_code('bonus.request')) or 'New'
        return res

    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee Name", required=False, )

    request_date = fields.Date(string="Today Date", required=False, default=fields.Date.context_today)

    bonus_amount = fields.Float(string="Bonus Amount", required=False, compute="get_bonus_amount")
    bonus_type = fields.Selection(string="", selection=[('amount', 'Amount'), ('days', 'Days'), ], required=False, )
    bonus_amount_amount = fields.Float(string="Bonus Amount", required=False, )
    bonus_amount_days = fields.Float(string="Bonus Days", required=False, )

    reason = fields.Text(string="Reason", required=False, )

    refundable_bonus = fields.Float(string="A Refundable Bonus", required=False, readonly=True, )

    contract_id = fields.Many2one(comodel_name="hr.contract", string="", required=False,
                                  related="employee_id.contract_id")

    day_value = fields.Float(string="", required=False, compute="_compute_day_value")
    is_overtime = fields.Boolean()
    det_type = fields.Selection(selection = [('default','Bonus Request'),
                                             ('sale','حافز المبيعات'),
                                             ('pay','حافز تحصيل'),
                                             ('manu','حافز انتاج'),
                                             ('ocs','منح و مناسبات'),
                                             ('trav','بدل سفر'),
                                             ('trans','بدل موصلات'),
                                             ('change','بدل طبيعة متغير'),
                                             ('car','بدل سيارة'),
                                            ],default = 'default')
    sale_percentage = fields.Float()
    batch_id = fields.Many2one('bonus.request.batch')
    @api.depends('employee_id', 'contract_id')
    def _compute_day_value(self):
        for rec in self:
            if rec.employee_id and rec.contract_id:
                rec.day_value = rec.contract_id.all / 30
            else:
                rec.day_value = 0.0
    max = fields.Float()
    min = fields.Float()
    def get_bonus_for_manu(self):
        return self.sale_percentage * self.contract_id.commission_wage_manu
    def get_bonus_for_sale(self):
        return self.sale_percentage * self.contract_id.commission_wage
    def adjust_amount(self,amount):
        if self.max < amount:
            return self.max
        if self.min > amount:
            return self.min
        return amount
    @api.depends('bonus_amount', 'bonus_type', 'bonus_amount_amount', 'bonus_amount_days', 'employee_id','det_type','sale_percentage','min','max')
    def get_bonus_amount(self):
        for rec in self:
            if rec.det_type == 'sale':
                rec.bonus_amount = rec.get_bonus_for_sale()
                continue
            if rec.det_type == 'manu':
                rec.bonus_amount = rec.get_bonus_for_manu()
                continue
            if rec.bonus_type == 'amount':
                rec.bonus_amount = rec.bonus_amount_amount
            elif rec.bonus_type == 'days':
                rec.bonus_amount = rec.bonus_amount_days * rec.day_value
            else:
                rec.bonus_amount = 0.0
            if rec.det_type == 'ocs':
                rec.bonus_amount = rec.adjust_amount(rec.bonus_amount)


    def approve(self):
        for rec in self:
            rec.state = 'confirm'
    def reject(self):
        self.state = 'rejected'

