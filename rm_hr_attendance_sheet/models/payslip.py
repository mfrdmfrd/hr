

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date
import math
from datetime import date, datetime, time

from .base_browsable import (
    BaseBrowsableObject,
    BrowsableObject,
    InputLine,
    Payslips,
    WorkedDays,
)
from odoo.tools import float_compare, float_is_zero, plaintext2html
from collections import defaultdict
from markupsafe import Markup

class HrPayslipCustom(models.Model):
    _inherit = 'hr.payslip'
#     def _action_create_account_move(self):
#         precision = self.env['decimal.precision'].precision_get('Payroll')

#         # Add payslip without run
#         payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)

#         # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
#         payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
#         for run in payslip_runs:
#             if run._are_payslips_ready():
#                 payslips_to_post |= run.slip_ids

#         # A payslip need to have a done state and not an accounting move.
#         payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)

#         # Check that a journal exists on all the structures
#         if any(not payslip.struct_id for payslip in payslips_to_post):
#             raise ValidationError(_('One of the contract for these payslips has no structure type.'))
#         if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
#             raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))

#         # Map all payslips by structure journal and pay slips month.
#         # {'journal_id': {'month': [slip_ids]}}
#         slip_mapped_data = defaultdict(lambda: defaultdict(lambda: self.env['hr.payslip']))
#         for slip in payslips_to_post:
#             slip_mapped_data[slip.struct_id.journal_id.id][slip.date or fields.Date().end_of(slip.date_to, 'month')] |= slip
#         for journal_id in slip_mapped_data: # For each journal_id.
#             line_ids = []
#             debit_sum = 0.0
#             credit_sum = 0.0
#             move_dict = {
#                 'narration': '',   
#             }
#             for slip_date in slip_mapped_data[journal_id]: # For each month.
#                 date = slip_date
#                 move_dict.update({
#                     'ref': fields.Date().end_of(slip.date_to, 'month').strftime('%B %Y'),
#                     'journal_id': journal_id,
#                     'date': date,
#                 })

#                 for slip in slip_mapped_data[journal_id][slip_date]:
#                     move_dict['narration'] += plaintext2html(slip.number or '' + ' - ' + slip.employee_id.name or '')
#                     move_dict['narration'] += Markup('<br/>')
#                     slip_lines = slip._prepare_slip_lines(date, line_ids)
#                     line_ids.extend(slip_lines)

#                 for line_id in line_ids: # Get the debit and credit sum.
#                     debit_sum += line_id['debit']
#                     credit_sum += line_id['credit']

#                 # The code below is called if there is an error in the balance between credit and debit sum.
#                 if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
#                     slip._prepare_adjust_line(line_ids, 'credit', debit_sum, credit_sum, date)
#                 elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
#                     slip._prepare_adjust_line(line_ids, 'debit', debit_sum, credit_sum, date)

#             # Add accounting lines in the move
#             move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
#             move = self._create_account_move(move_dict)
#             for slip in slip_mapped_data[journal_id][slip_date]:
#                 slip.write({'move_id': move.id, 'date': date})
#         return True

    contract_id = fields.Many2one(
        'hr.contract', string='Contract', domain="[('company_id', '=', company_id)]",
        compute='_compute_contract_id', store=True, readonly=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]})

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_contract_id(self):
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                slip.contract_id = False
                continue
            # Add a default contract if not already defined or invalid
            if slip.contract_id and slip.employee_id == slip.contract_id.employee_id:
                continue
            contracts = slip.employee_id._get_contracts(slip.date_from, slip.date_to)
            slip.contract_id = contracts[0] if contracts else False

    @api.depends('employee_id', 'struct_id', 'date_from')
    def _compute_name(self):
        for slip in self.filtered(lambda p: p.employee_id and p.date_from):
            # lang = slip.employee_id.sudo().address_home_id.lang or self.env.user.lang
            # context = {'lang': lang}
            payslip_name = slip.struct_id.payslip_name or _('Salary Slip')
            # del context

            slip.name = '%(payslip_name)s - %(employee_name)s - %(dates)s' % {
                'payslip_name': payslip_name,
                'employee_name': slip.employee_id.name,
                'dates': format_date(self.env, slip.date_from, date_format="MMMM y") #, lang_code=lang)
            }

    def compute_sheet(self):
        for payslip in self:
            # delete old payslip lines
            payslip.line_ids.unlink()
            # write payslip lines
            number = payslip.number or self.env["ir.sequence"].next_by_code(
                "salary.slip"
            )
            lines = [(0, 0, line) for line in list(payslip.get_lines_dict().values())]
            payslip.write(
                {
                    "line_ids": lines,
                    "number": number,
                    "state": "verify",
                    "compute_date": fields.Date.today(),
                }
            )
        return True

    def _get_employee_contracts(self):
        contracts = self.env["hr.contract"]
        for payslip in self:
            if payslip.contract_id.ids:
                contracts |= payslip.contract_id
            else:
                contracts |= payslip.employee_id._get_contracts(
                    date_from=payslip.date_from, date_to=payslip.date_to
                )
        return contracts

    def _init_payroll_dict_contracts(self):
        return {
            "count": 0,
        }

    def get_payroll_dict(self, contracts):
        """Setup miscellaneous dictionary values.
        Other modules may overload this method to inject discreet values into
        the salary rules. Such values will be available to the salary rule
        under the `payroll.` prefix.

        This method is evaluated once per payslip.
        :param contracts: Recordset of all hr.contract records in this payslip
        :return: a dictionary of discreet values and/or Browsable Objects
        """
        self.ensure_one()

        res = {
            # In salary rules refer to this as: payroll.contracts.count
            "contracts": BaseBrowsableObject(self._init_payroll_dict_contracts()),
        }
        res["contracts"].count = len(contracts)

        return res

    def _get_baselocaldict(self, contracts):
        self.ensure_one()
        worked_days_dict = {
            line.code: line for line in self.worked_days_line_ids if line.code
        }
        input_lines_dict = {
            line.code: line for line in self.input_line_ids if line.code
        }
        localdict = {
            "payslips": Payslips(self.employee_id.id, self, self.env),
            "worked_days": WorkedDays(self.employee_id.id, worked_days_dict, self.env),
            "inputs": InputLine(self.employee_id.id, input_lines_dict, self.env),
            "payroll": BrowsableObject(
                self.employee_id.id, self.get_payroll_dict(contracts), self.env
            ),
            "current_contract": BrowsableObject(self.employee_id.id, {}, self.env),
            "categories": BrowsableObject(self.employee_id.id, {}, self.env),
            "rules": BrowsableObject(self.employee_id.id, {}, self.env),
            "result_rules": BrowsableObject(self.employee_id.id, {}, self.env),
            "tools": BrowsableObject(
                self.employee_id.id, self._get_tools_dict(), self.env
            ),
        }
        return localdict

    def _get_tools_dict(self):
        # _get_tools_dict() is intended to be inherited by other private modules
        # to add tools or python libraries available in localdict
        return {
            "math": math,
            "datetime": datetime,
        }  # "math" object is useful for doing calculations


    def get_lines_dict(self):
        lines_dict = {}
        blacklist = []
        for payslip in self:
            contracts = payslip._get_employee_contracts()
            baselocaldict = payslip._get_baselocaldict(contracts)
            for contract in contracts:
                # assign "current_contract" dict
                baselocaldict["current_contract"] = BrowsableObject(
                    payslip.employee_id.id,
                    {},
                    payslip.env,
                )
                # set up localdict with current contract and employee values
                localdict = dict(
                    baselocaldict,
                    employee=contract.employee_id,
                    contract=contract,
                    payslip=payslip,
                )
                for rule in payslip._get_salary_rules():
                    localdict = rule._reset_localdict_values(localdict)
                    # check if the rule can be applied
                    if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                        localdict, _dict = payslip._compute_payslip_line(
                            rule, localdict, lines_dict
                        )
                        lines_dict.update(_dict)
                    else:
                        # blacklist this rule and its children
                        blacklist += [
                            id for id, seq in rule._recursive_search_of_rules()
                        ]
                # call localdict_hook
                localdict = payslip.localdict_hook(localdict)
                # reset "current_contract" dict
                baselocaldict["current_contract"] = {}
        return lines_dict

    def _get_salary_rules(self):
        rule_obj = self.env["hr.salary.rule"]
        sorted_rules = rule_obj
        for payslip in self:
            contracts = payslip._get_employee_contracts()
            if len(contracts) == 1 and payslip.struct_id:
                structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
            else:
                structure_ids = contracts.get_all_structures()
            rule_ids = (
                self.env["hr.payroll.structure"].browse(structure_ids).get_all_rules()
            )
            sorted_rule_ids = [
                id for id, sequence in sorted(rule_ids, key=lambda x: x[1])
            ]
            sorted_rules |= rule_obj.browse(sorted_rule_ids)
        return sorted_rules

    def _prepare_line_values(self, line, account_id, date, debit, credit):
        return {
            'name': line.name,
            'partner_id': self.employee_id.address_home_id.id,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'date': date,
            'debit': debit,
            'credit': credit,
            'analytic_account_id': line.salary_rule_id.analytic_account_id.id or line.slip_id.contract_id.analytic_account_id.id,
        }

    def _prepare_adjust_line(self, line_ids, adjust_type, debit_sum, credit_sum, date):
        acc_id = self.sudo().journal_id.default_account_id.id
        if not acc_id:
            raise UserError(_('The Expense Journal "%s" has not properly configured the default Account!') % (self.journal_id.name))
        existing_adjustment_line = (
            line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
        )
        adjust_credit = next(existing_adjustment_line, False)

        if not adjust_credit:
            adjust_credit = {
                'name': _('Adjustment Entry'),
                'partner_id': self.employee_id.address_home_id.id,
                'account_id': acc_id,
                'journal_id': self.journal_id.id,
                'date': date,
                'debit': 0.0 if adjust_type == 'credit' else credit_sum - debit_sum,
                'credit': debit_sum - credit_sum if adjust_type == 'credit' else 0.0,
            }
            line_ids.append(adjust_credit)
        else:
            adjust_credit['credit'] = debit_sum - credit_sum


    def send_payslip(self):
        print("ahmed saber elsayed")
        """
                This function opens a window to compose an email, with the edi payslip template message loaded by default
                """
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('send_email_payslips', 'email_template_hr_payslip')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'hr.payslip',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

class HrPayslipWorkedDays(models.Model):
    """Create new model for adding some fields"""
    _inherit = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'


    work_entry_type_id = fields.Many2one('hr.work.entry.type', index=True, default=lambda self: self.env['hr.work.entry.type'].search([], limit=1))
