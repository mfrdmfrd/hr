import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import math, pytz
from odoo.tools import float_round


_logger = logging.getLogger(__name__)


class AttendanceWizard(models.TransientModel):
    _name = 'attendance.wizard'
    _description = 'Attendance Wizard'

    @api.model
    def _get_all_device_ids(self):
        all_devices = self.env['attendance.device'].search([('state', '=', 'confirmed')])
        if all_devices:
            return all_devices.ids
        else:
            return []

    device_ids = fields.Many2many('attendance.device', string='Devices', default=_get_all_device_ids, domain=[('state', '=', 'confirmed')])
    fix_attendance_valid_before_synch = fields.Boolean(string='Fix Attendance Valid', help="If checked, Odoo will recompute all attendance data for their valid"
                                                     " before synchronizing with HR Attendance (upon you hit the 'Synchronize Attendance' button)")

    # def download_attendance_manually(self):
    #     # TODO: remove me after 12.0
    #     self.action_download_attendance()

    def action_download_attendance(self):
        if not self.device_ids:
            raise UserError(_('You must select at least one device to continue!'))
        self.device_ids.action_attendance_download()

    # def download_device_attendance(self):
    #     # TODO: remove me after 12.0
    #     self.cron_download_device_attendance()

    def cron_download_device_attendance(self):
        devices = self.env['attendance.device'].search([('state', '=', 'confirmed')])

        devices.action_attendance_download()
        
        
    def cron_user_attendance_validate(self):
        # user_attendance = self.env['user.attendance']
        # user_attendance.action_attendace_validated()
        return

    def float_to_time(self,hours, moment='am'):
        """ Convert a number of hours into a time object. """
        if hours == 12.0 and moment == 'pm':
            return time.max
        fractional, integral = math.modf(hours)
        if moment == 'pm':
            integral += 12
        return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)

    def cron_sync_attendance(self,days_count=30):
        self.with_context(synch_ignore_constraints=True).sync_attendance(days_count)

    def sync_attendance(self,days_count=30):
        """
        This method will synchronize all downloaded attendance data with Odoo attendance data.
        It do not download attendance data from the devices.
        """

        time_margin = 2
        synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
        DeviceUserAttendance = self.env['user.attendance']
        HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)
        activity_ids = self.env['attendance.activity'].search([])
        # error_msg = {}

        # if self.fix_attendance_valid_before_synch:
        # data_to_process = DeviceUserAttendance.search([('is_attedance_created', '=', False),])
        #self.action_fix_user_attendance_valid()
        #self.env['user.attendance'].action_attendace_validated()


        last_employee_attendance = {}
        # for activity_id in activity_ids:
        #     if activity_id.id not in last_employee_attendance.keys():
        #         last_employee_attendance[activity_id.id] = {}

            # ('valid', '=', True),

        current_date = date.today()
        unsync_data = DeviceUserAttendance.search([('is_attedance_created', '=', False),
                                                   ('hr_attendance_id', '=', False),
                                                   ('employee_id', '!=', False),
                                                   ('timestamp','<', datetime.now() - timedelta(hours=24))],
                                                  order='timestamp ASC')

        for employee_id in self.env['hr.employee'].search([('active','=', True)]): #,('id','=',9227)]):
            # employee_attendances = unsync_data.search([('employee_id','=',employee_id.id),
            #                                             ('is_attedance_created', '=', False),
            #                                             ('hr_attendance_id', '=', False),
            #                                             ('employee_id', '!=', False),
            #                                             ('timestamp', '<', datetime.now() - timedelta(hours=24))],
            #                                             order = 'timestamp ASC'
            #                                             )
            employee_attendances = unsync_data.filtered(lambda a: a.employee_id.id==employee_id.id)

            if employee_attendances:
                employee_calendar = employee_id.resource_calendar_id

                for day_counter in range(days_count):
                    day_to_process = current_date - timedelta(day_counter)
                    calendar_attendance = employee_calendar.attendance_ids.search([
                        ('calendar_id','=', employee_calendar.id),
                        ('dayofweek', '=', day_to_process.weekday()),
                        ])
                    # calendar_attendance = employee_calendar.attendance_ids.filtered(lambda a:
                    #                                                                 a.calendar_id.id == employee_calendar.id and
                    #                                                                 a.dayofweek == day_to_process.weekday())

                    if calendar_attendance:
                        att_start = calendar_attendance[0].hour_from
                        att_end = calendar_attendance[0].hour_to
                        for catt in calendar_attendance:
                            att_start = min(att_start,catt.hour_from)
                            att_end = max(att_end,catt.hour_to)

                        tz = pytz.timezone(employee_id.tz)

                        datetime_start_tz = datetime.combine(day_to_process,self.float_to_time(att_start-time_margin))
                        datetime_start_tz = tz.localize(datetime_start_tz)
                        datetime_end_tz = datetime.combine(day_to_process,self.float_to_time(att_end+time_margin))
                        datetime_end_tz = tz.localize(datetime_end_tz)

                        datetime_start = datetime_start_tz.astimezone(pytz.utc).replace(tzinfo=None)
                        datetime_end = datetime_end_tz.astimezone(pytz.utc).replace(tzinfo=None)

                        if datetime_start > datetime_end:
                            datetime_end = datetime_end + relativedelta(days=+1)


                        if datetime_start > datetime_end:
                            raise UserError('Invalid dates')

                        employee_day_attendances = employee_attendances.filtered(lambda a: a.timestamp > datetime_start and
                                                                                a.timestamp < datetime_end)

                        if employee_day_attendances:
                            first_att = employee_day_attendances[0]
                            last_att = employee_day_attendances[-1]

                            hr_attendance_id = HrAttendance.search([
                                ('employee_id', '=', employee_id.id),
                                ('check_in', '=', first_att.timestamp)],
                                limit=1)
                            if not hr_attendance_id:
                                try:
                                    vals = {
                                        'employee_id': employee_id.id,
                                        'check_in': first_att.timestamp,
                                        'check_out': last_att.timestamp,
                                        'checkin_device_id': first_att.device_id.id,
                                        'checkout_device_id': last_att.device_id.id,
                                        'activity_id': first_att.activity_id.id,
                                    }
                                    hr_attendance_id = HrAttendance.create(vals)
                                except Exception as e:
                                    _logger.error(e)

                                if hr_attendance_id:
                                    for att in employee_day_attendances:
                                        att.write({
                                            'hr_attendance_id': hr_attendance_id.id
                                        })
                            else:
                                _logger.error(f'Attendance duplicate, can not create, {employee_id.name},{day_to_process},{hr_attendance_id.id}')

                    #     hr_attendance_id.write({
                    #         'check_out': last_att.timestamp,
                    #     })
                    #     for att in employee_attendances:
                    #         for att in employee_day_attendances:
                    #             att.write({
                    #                 'hr_attendance_id': hr_attendance_id.id
                    #             })




                    # if employee_id.id not in last_employee_attendance[activity_id.id].keys():
                    #     last_employee_attendance[activity_id.id][employee_id.id] = False

                    # if att.type == 'checkout':
                    #     # find last attendance
                    #     last_employee_attendance[activity_id.id][employee_id.id] = HrAttendance.search(
                    #         [('employee_id', '=', employee_id.id),
                    #          ('activity_id', 'in', (activity_id.id, False)),
                    #          ('check_in', '<=', att.timestamp)], limit=1, order='check_in DESC')
                    #
                    #     hr_attendance_id = last_employee_attendance[activity_id.id][employee_id.id]

                        # if hr_attendance_id:
                        #     try:
                        #         hr_attendance_id.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                        #             'check_out': att.timestamp,
                        #             'checkout_device_id': att.device_id.id
                        #             })
                        #     except ValidationError as e:
                        #         if att.device_id not in error_msg:
                        #             error_msg[att.device_id] = ""

                    #             msg = ""
                    #             att_check_time = fields.Datetime.context_timestamp(att, att.timestamp)
                    #             msg += str(e) + "<br />"
                    #             msg += _("'Check Out' time cannot be earlier than 'Check In' time. Debug information:<br />"
                    #                           "* Employee: <strong>%s</strong><br />"
                    #                           "* Type: %s<br />"
                    #                           "* Attendance Check Time: %s<br />") % (employee_id.name, att.type, fields.Datetime.to_string(att_check_time))
                    #             _logger.error(msg)
                    #             error_msg[att.device_id] += msg
                    # else:
                    #     # create hr attendance data
                    #     vals = {
                    #         'employee_id': employee_id.id,
                    #         'check_in': att.timestamp,
                    #         'checkin_device_id': att.device_id.id,
                    #         'activity_id': activity_id.id,
                    #         }
                    #     hr_attendance_id = HrAttendance.search([
                    #         ('employee_id', '=', employee_id.id),
                    #         ('check_in', '=', att.timestamp),
                    #         ('checkin_device_id', '=', att.device_id.id),
                    #         ('activity_id', '=', activity_id.id)], limit=1)
                    #     if not hr_attendance_id:
                    #         try:
                    #             # pass
                    #             hr_attendance_id = HrAttendance.create(vals)
                    #
                    #         except Exception as e:
                    #             _logger.error(e)
                    #
                    # if hr_attendance_id:
                    #     att.write({
                    #         'hr_attendance_id': hr_attendance_id.id
                    #         })

        # if bool(error_msg):
        #     for device in error_msg.keys():
        #
        #         if not device.debug_message:
        #             continue
        #         # device.message_post(body=error_msg[device])

    def clear_attendance(self):
        if not self.device_ids:
            raise (_('You must select at least one device to continue!'))
        if not self.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            raise UserError(_('Only HR Attendance Managers can manually clear device attendance data'))

        for device in self.device_ids:
                device.clearAttendance()

    def action_fix_user_attendance_valid(self):
        all_attendances = self.env['user.attendance'].search([])
        for attendance in all_attendances:
            if attendance.is_valid():
                attendance.write({'valid': True})
            else:
                attendance.write({'valid': False})



