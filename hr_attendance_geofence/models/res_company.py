from odoo import fields, models, api

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    attendance_geofence = fields.Boolean(string="Attendances Geofence", default=False)