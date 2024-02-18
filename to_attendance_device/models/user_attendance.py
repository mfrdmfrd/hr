from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from odoo import exceptions
from dateutil.relativedelta import relativedelta
from odoo.tools import float_round
import math,time

class UserAttendance(models.Model):
    _name = 'user.attendance'
    _description = 'User Attendance'
    _order = 'timestamp DESC, user_id, status, attendance_state_id, device_id'

    device_id = fields.Many2one('attendance.device', string='Attendance Device', required=True, ondelete='restrict',
                                index=True)
    user_id = fields.Many2one('attendance.device.user', string='Device User', required=True, ondelete='cascade',
                              index=True)
    timestamp = fields.Datetime(string='Timestamp', required=True, index=True)
    status = fields.Integer(string='Device Attendance State', required=True,
                            help='The state which is the unique number stored in the device to'
                                 ' indicate type of attendance (e.g. 0: Checkin, 1: Checkout, etc)')
    attendance_state_id = fields.Many2one('attendance.state', string='Odoo Attendance State',
                                          help='This technical field is to map the attendance'
                                               ' status stored in the device and the attendance status in Odoo',
                                          required=True, index=True)
    activity_id = fields.Many2one('attendance.activity', related='attendance_state_id.activity_id', store=True,
                                  index=True)
    hr_attendance_id = fields.Many2one('hr.attendance', string='HR Attendance', ondelete='set null',
                                       help='The technical field to link Device Attendance Data with Odoo\' Attendance Data',
                                       index=True)

    type = fields.Selection([('checkin', 'Check-in'),
                             ('checkout', 'Check-out')], string='Activity Type', related='attendance_state_id.type',
                            store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related='user_id.employee_id', store=True,
                                  index=True)
    valid = fields.Boolean(string='Valid Attendance', index=True, readonly=True, default=False,
                           help="This field is to indicate if this attendance record is valid for HR Attendance Synchronization."
                                " E.g. The Attendances with Check out prior to Check in or the Attendances for users without employee"
                                " mapped will not be valid.")
    is_attedance_created = fields.Boolean(string="Is Attendance")

    _sql_constraints = [
        ('unique_user_id_device_id_timestamp',
         'UNIQUE(user_id, device_id, timestamp)',
         "The Timestamp and User must be unique per Device"),
    ]

    def cron_download_device_attendance(self):
        devices = self.env['attendance.device'].search([('state', '=', 'confirmed')])
        devices.action_attendance_download()

    @api.constrains('status', 'attendance_state_id')
    def constrains_status_attendance_state_id(self):
        for r in self:
            if r.status != r.attendance_state_id.code:
                raise (
                    _('Attendance Status conflict! The status number from device must match the attendance status defined in Odoo.'))

    def is_valid(self):
        self.ensure_one()
        if not self.employee_id:
            return False
        attendances = self.env['user.attendance']
        calendar_id = self.employee_id.resource_calendar_id
        calendar_attendance_id = calendar_id.attendance_ids.search([
            ('calendar_id', '=', calendar_id.id),
            ('dayofweek', '=', self.timestamp.weekday())])
        search_filter = [('employee_id', '=', self.employee_id.id),
                                ('timestamp', '<', self.timestamp),
                                ('timestamp', '>', self.timestamp - timedelta(hours=18)),
                                ('activity_id', '=', self.activity_id.id)]
        span_next_day = False
        for c in calendar_attendance_id:
            if c.span_next_day:
                span_next_day = True
        if not span_next_day:
            search_filter.append(
                ('timestamp', '>', self.timestamp.replace(hour=0,minute=0,second=1))
            )
        prev_att = attendances.search(search_filter, limit=1, order='timestamp DESC')

        if not prev_att:
            if self.type == 'checkin':
                valid = True
            else:
                #if checkout instead of checkin, convert to checkin
                # self.update({'type': 'checkin',})
                # checkin_state = self.env['attendance.state'].search(
                #     [('activity_id', '=', self.attendance_state_id.activity_id.id), ('type', '=', 'checkin')])
                # self.write({'status': 0,
                #             'attendance_state_id': checkin_state.id})
                #
                # # self.update({'attendance_state_id': checkin_state.id})

                valid = False
        else:
            if self.type == 'checkout' and prev_att.type == 'checkout' and prev_att.valid:
                prev_att.write({'valid': False})
                valid = True
            # elif self.type == 'checkin' and prev_att.type == 'checkin' and prev_att.valid:
            #     #if checkin again, convert to checkout
            #     # self.write({'type': 'checkout'})
            #     checkout_state = self.env['attendance.state'].search(
            #         [('activity_id', '=', self.attendance_state_id.activity_id.id), ('type', '=', 'checkout')])
            #     self.update({'attendance_state_id': checkout_state.id})
            #     valid = True
            # elif self.type == 'checkin' and prev_att.type == 'checkout':
            #     # self.update({'type': 'checkout'})
            #     self.write({'attendance_state_id': 1})
            #     # prev_att.update({'type': 'checkin'})
            #     prev_att.write({'attendance_state_id': 0})
            #     prev_att.write({'valid': True})
            #     valid = True
            else:
                valid = prev_att.type != self.attendance_state_id.type and True or False
        return valid

    @api.model_create_multi
    def create(self, vals_list):
        attendances = super(UserAttendance, self).create(vals_list)
        valid_attendances = attendances.filtered(lambda att: att.is_valid())
        if valid_attendances:
            valid_attendances.write({'valid': True})
        return attendances

    def check_validation(self):
        for att in self:
            att.write({'valid': att.is_valid()})

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def float_to_time(hours, moment='am'):
        """ Convert a number of hours into a time object. """
        if hours == 12.0 and moment == 'pm':
            return time.max
        fractional, integral = math.modf(hours)
        if moment == 'pm':
            integral += 12
        return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)

    def action_attendace_validated(self):
        # self.check_validation()

        current_date = fields.date.today()
        for day_counter in range(100):
            day_to_process = current_date - timedelta(day_counter)
            date_start = day_to_process + relativedelta(seconds=0)
            date_end = day_to_process + relativedelta(days= 1, seconds=-1)
            all_employees = self.env['hr.employee'].search([])
            for employee in all_employees:
                user_attendance = self.env['user.attendance']
                count = user_attendance.search_count([('employee_id', '=', employee.id)])
                if count:
                    employee_attendance_list_all = user_attendance.search(
                        [('employee_id', '=', employee.id), ('timestamp', '>=', date_start), ('timestamp', '<=', date_end),
                        ('is_attedance_created', '=', False)], order="timestamp asc", )
                    # attendance_list_all.validate()
                    attendance_list = employee_attendance_list_all.filtered(lambda att: att.valid is True)

                    if attendance_list:
                        for attendace in attendance_list:
                            #Check if there is an existing attendance without checkout in the same day before this att-entry
                            existing_attendance = self.env['hr.attendance'].search(
                                [('employee_id', '=', attendace.employee_id.id), ('check_in', '<=', attendace.timestamp),
                                 ('check_in', '>=', date_start), ('check_out', '=', False)])
                            #search all or the day??? add ('check_in', '>=', date_start),
                            if existing_attendance:
                                #put this att-entry as a checkout
                                existing_attendance.update({
                                    'check_out': attendace.timestamp,
                                })
                                # do not process again
                                attendace.update({
                                    'is_attedance_created': True
                                })
                            else:
                                #check if there is an existing attendance with no checkout after this att-entry
                                conflict_in_attendance = self.env['hr.attendance'].search(
                                    [('employee_id', '=', attendace.employee_id.id),
                                     ('check_in', '>=', attendace.timestamp),
                                     ('check_out', '=', False)])
                                if conflict_in_attendance:
                                    # update the checkin with the new entry
                                    conflict_in_attendance.update({
                                        'check_in': attendace.timestamp,
                                    })
                                    # do not process again
                                    attendace.update({
                                        'is_attedance_created': True
                                    })
                                else:
                                    #check if there is an existing attendance with checkin and checkout before this att-entry
                                    conflict_out_attendance = self.env['hr.attendance'].search(
                                        [('employee_id', '=', attendace.employee_id.id),
                                         ('check_in', '<=', attendace.timestamp),
                                         ('check_out', '<=', attendace.timestamp)])
                                    if conflict_out_attendance:
                                        #correct checkout to this att-entry
                                        conflict_out_attendance.update({
                                            'check_out': attendace.timestamp,
                                            'checkout_device_id': attendace.device_id.id,
                                        })
                                        attendace.update({
                                            'is_attedance_created': True
                                        })
                                    else:
                                        #create attendace
                                        vals = {
                                            'employee_id': attendace.employee_id.id,
                                            'check_in': attendace.timestamp,
                                            'checkin_device_id': attendace.device_id.id,
                                        }
                                        hr_attendance = self.env['hr.attendance'].create(vals)
                                        attendace.update({
                                            'is_attedance_created': True
                                        })
