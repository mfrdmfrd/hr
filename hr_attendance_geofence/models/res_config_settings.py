from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    attendance_geofence = fields.Boolean(related="company_id.attendance_geofence", string="Geofence", readonly=False)