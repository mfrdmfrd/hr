# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from math import floor,ceil
AARDA_DAYS_AMOUNT = 6
ETYADY_DAYS_AMOUNT = 15
DAYS_TOTAl = AARDA_DAYS_AMOUNT + ETYADY_DAYS_AMOUNT

class hr_custom_3(models.Model):
    _inherit = 'hr.employee'
    joining_date = fields.Date()
    @api.onchange('joining_date')
    def _set_joining_date(self):
        for contract in self.contract_ids:
            contract.joining_date = self.joining_date 
class hr_custom_2(models.Model):
    _inherit = 'hr.contract'
    resg_date = fields.Date()
    joining_date = fields.Date()
    first_allocation_created = fields.Boolean()
    def create_yearly_util(self,type_name,emps,duration,date_start = False,date_end = False):
        if not(emps):
            return
        today = self.get_today()
        last_month_day = datetime(today.year,12,31)
        date_end = date_end or last_month_day
        date_start = date_start or today
        allocation_type = self.env['hr.leave.type'].search([('name','ilike',type_name)])
        vals = {
            'holiday_status_id' : allocation_type[0].id,
            'allocation_type' : 'regular',
            'date_from' : date_start,
            'date_to' : date_end,
            'holiday_type' : 'employee',
            'employee_ids' : [(6,0,emps.ids)],
            'name' : 'Yearly Allocation',
            'number_of_days' :duration,
            'multi_employee' : True
        }
        allocation = self.env["hr.leave.allocation"].create(vals)
        allocation.action_confirm()
        allocation.action_validate()
    def get_today(self):
        today = fields.Date().today()
        return today
    def create_yearly_mid_year(self):
        today = self.get_today()
        today = datetime(today.year,today.month,1)
        min_joinin_date = today - relativedelta(months = +6)
        month_days = monthrange(min_joinin_date.year,min_joinin_date.month)[1]
        last_joinin_date = min_joinin_date + timedelta(days = month_days - 1)
        valid_contracts = self.env['hr.contract'].search([('joining_date','<=',last_joinin_date),('joining_date','>=',min_joinin_date),('state','=','open')])
        emps = valid_contracts.mapped(lambda contract : contract.employee_id)
        months_factor = (12 - today.month + 1) / 12
        aarda_amount = AARDA_DAYS_AMOUNT * months_factor
        etyady_amount = ETYADY_DAYS_AMOUNT * months_factor
        self.create_yearly_util('أجازة عارضة',emps,aarda_amount)
        self.create_yearly_util('أجازة اعتيادية',emps,etyady_amount)
        

    def create_yearly_first_day_in_year(self):
        today = self.get_today()
        min_joinin_date = datetime(today.year - 1,7,1)
        valid_contracts = self.env['hr.contract'].search([('joining_date','<=',min_joinin_date),('state','=','open')])
        emps = valid_contracts.mapped(lambda contract : contract.employee_id)
        self.create_yearly_util('أجازة عارضة',emps,AARDA_DAYS_AMOUNT)
        self.create_yearly_util('أجازة اعتيادية',emps,ETYADY_DAYS_AMOUNT)
    def create_yearly_alloc(self):
        today = self.get_today()
        if today.month == 1 and today.day == 1:
            self.create_yearly_first_day_in_year()
            return
        if today.day == 1:
            self.create_yearly_mid_year()
            
            
        
    @api.onchange('employee_id')
    def _get_joining_date(self):
        self.joining_date = self.employee_id.joining_date
    @api.onchange('joining_date')
    def _set_joining_date(self):
        self.employee_id.joining_date = self.joining_date 
    @api.model
    def create(self,vals):
        res = super().create(vals)
        res.joining_date = res.employee_id.joining_date
        return res
    def mailmessage(self):
        notification_ids = [(0, 0,
         {
             'res_partner_id': self.hr_responsible_id.partner_id.id,
             'notification_type': 'inbox'
         }
         )]
        vals = {
             'email_from': self.env.user.partner_id.email, # add the sender email
             'author_id': self.env.user.partner_id.id, # add the creator id
             'subtype_id': self.env.ref('mail.mt_comment').id, #Leave this as it is
             'body': 'contract about to expire', # here add the message body
            'record_name' : self.name,
            'notification_ids': notification_ids,
            'model' : 'hr.contract',
            'res_id' : self.id,
            'message_type': 'comment'
          }        
        m = self.env['mail.message'].create(vals)
    def is_contract_ended(self):
        today = fields.Date.today() + timedelta(days=15)
        contracts_ended = self.env['hr.contract'].search([('state','=','open'),('date_end','<=',today)])
        for contract in contracts_ended:
            contract.mailmessage()
    transportation_allowance = fields.Float('بدل مواصلات')
    safe_allowance = fields.Float('بدل خزينة')
    food_allowance = fields.Float('بدل وجبة')
    live_allowance = fields.Float('بدل غلاء معيشة')
    work_nature_allowance = fields.Float('بدل طبيعة عمل')
    social_allowance = fields.Float('علاوه اجتماعية ')
    other_allowance = fields.Float('البدلات و المزايا')
    all = fields.Float('الشامل',compute = '_set_all',readonly = False,store = True)
    @api.depends('other_allowance','wage')
    def _set_all(self):
        for rec in self:
            rec.all = rec.wage + rec.other_allowance 
    sub_salary = fields.Float('أجر الاشتراك')
    allowance_salary = fields.Float('الراتب التأميني')
    purchase_insurance = fields.Float('شراء مدة تأمنية')
    d_union = fields.Float('اشتراك تقابة')
    union_box = fields.Float('صندوق نقابة')
    purchase_insurance_med = fields.Float('اشتراك تأمين طبي')
    on_box = fields.Float('صندوق الزامات')
    charity = fields.Float('تبرعات خارجية')
    ins_insurance = fields.Float('قسط بوليصة تأمين')
    
    
    

    worker_share = fields.Float(compute = '_compute_share',string = 'حصه العامل')
    company_share = fields.Float(compute = '_compute_share',string = 'حصه الشركة')
    intern_date_start = fields.Date('تاريخ بدايه الاختبار')
    intern_date_end = fields.Date(readonly = True,string = 'تاريخ نهاية الاختبار')
    @api.onchange('intern_date_start')
    def _set_intern_date_end(self):
        self.intern_date_end = self.intern_date_start + timedelta(days=90) if self.intern_date_start else False
    @api.depends('allowance_salary')
    def _compute_share(self):
        for rec in self:
            rec.worker_share = 0.11 * rec.allowance_salary
            rec.company_share = (18.75 / 100) * rec.allowance_salary
            
    





class hr_custom(models.Model):
    _inherit = 'hr.employee'
    _sql_constraints = [ ('unique_code', 'UNIQUE(employee_code)', 'Code must be unique.'),
]
    age = fields.Integer(compute = '_set_age')
    @api.depends('birthday')
    def _set_age(self):
        for rec in self:
            if rec.birthday:
                today = fields.Date().today()
                birthdate = rec.birthday
                age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
                rec.age = age
            else:
                rec.age = 0
    my_address = fields.Char('العنوان')
    employee_code = fields.Char('كود الموظف')
    insurance_code = fields.Char('الرقم التاميني')
    isnurance_job = fields.Char('الوظيفة بالتامينات')
    skill_level = fields.Char('قياس مهارة')
    coming_number = fields.Char('رقم الوارد')
    coming_date = fields.Date('تاريخ الوارد')
    medical_check_cret = fields.Boolean('استمارة كشف طبى')
    medical_check = fields.Boolean('كشف طبي')
    recieved_check_id = fields.Boolean('استلام بطاقة الكشف')
    file_number = fields.Char('رقم الملف')
    add_number = fields.Char('رقم القيد')
    license_number = fields.Char('رقم الرخصة')
    license_date_end = fields.Char('تاريخ انتهاء الرخصة')
    millitary_cert_number = fields.Char('رقم شهادة التجنيد')
    military_service_position = fields.Selection(string="", selection=[('not_applicable', 'not applicable'),
                                                                       ('Exempted', 'Exempted'),
                                                                       ('Completed', 'Completed'),
                                                                       ('Postponed', 'Postponed'), ], required=False, )
    bank_number = fields.Char('رقم الحساب البنكى')
    trans_place = fields.Char('مكان الركوب')
    line_1 = fields.Char('خط المواصلات اولى')
    line_2 = fields.Char('خط المواصلات تانية')
    line_3 = fields.Char('خط المواصلات تالتة')

        
