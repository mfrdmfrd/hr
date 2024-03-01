from odoo import http, _
from odoo.http import request
import datetime
from odoo.addons.hr_attendance.controllers.main import HrAttendance as HrAttendance

class HrAttendance(HrAttendance):

    @staticmethod
    def _get_employee_info_response(employee):
        response = {}
        if employee:
            response = {
                'id': employee.id,
                'employee_name': employee.name,
                'employee_avatar': employee.image_1920,
                'hours_today': employee.hours_today,
                'total_overtime': employee.total_overtime,
                'last_attendance_worked_hours': employee.last_attendance_worked_hours,
                'last_check_in': employee.last_check_in,
                'attendance_state': employee.attendance_state,
                'hours_previously_today': employee.hours_previously_today,
                'kiosk_delay': employee.company_id.attendance_kiosk_delay * 1000,
                'attendance': {
                    'id': employee.last_attendance_id.id or False,
                    'check_in': employee.last_attendance_id.check_in,
                    'check_out': employee.last_attendance_id.check_out
                    },
                'overtime_today': request.env['hr.attendance.overtime'].sudo().search([
                    ('employee_id', '=', employee.id), ('date', '=', datetime.date.today()),
                    ('adjustment', '=', False)]).duration or 0,
                'use_pin': employee.company_id.attendance_kiosk_use_pin,
                'display_systray': employee.company_id.attendance_from_systray,
                'display_overtime': employee.company_id.hr_attendance_display_overtime,
                'attendance_geofence': employee.company_id.attendance_geofence,
            }
        return response
    
    @http.route('/hr_attendance/attendance_res_config', type="json", auth="public")
    def attendance_res_config(self, token):
        company = self._get_company(token)
        conf = {}
        if company:
            conf['attendance_geofence'] = company.attendance_geofence
        return conf
    
    @http.route('/hr_attendance/get_geofences', type="json", auth="public")
    def get_geofences(self, company_id=False, employee_id=False):
        if not company_id or not employee_id:
            return []
        geofences = request.env['hr.attendance.geofence'].sudo().search_read((['company_id', '=', int(company_id)],['employee_ids', 'in', int(employee_id)]))
        return geofences
    
    @http.route('/hr_attendance/update_checkin_geofence', type="json", auth="public")
    def update_checkin_geofence(self, token, attendance_id, geofences):
        company = self._get_company(token)
        if company:
            attendance = request.env['hr.attendance'].sudo().browse(attendance_id)
            if attendance:
                attendance.sudo().write({
                    'check_in_geofence_ids': geofences
                })
        return {}
    
    @http.route('/hr_attendance/update_checkout_geofence', type="json", auth="public")
    def update_checkout_geofence(self, token, attendance_id, geofences):
        company = self._get_company(token)
        if company:
            attendance = request.env['hr.attendance'].sudo().browse(attendance_id)
            if attendance:
                attendance.sudo().write({
                    'check_out_geofence_ids': geofences
                })
        return {}