

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

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

