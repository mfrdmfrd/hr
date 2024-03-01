/** @odoo-module **/

import public_kiosk_app from "@hr_attendance/public_kiosk/public_kiosk_app";
const kioskAttendanceApp = public_kiosk_app.kioskAttendanceApp;

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { AttendanceGeofenceDialog } from "./attendance_geofence_dialog"

patch(kioskAttendanceApp.prototype, {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");
        this.loadResConfig();
    },
    async loadResConfig(){
        const result = await this.rpc("/hr_attendance/attendance_res_config" ,{
            'token': this.props.token,
        });
        this.res_config = result;
       
        if (this.res_config && this.res_config.attendance_geofence) {
            const attendance_geofence = this.res_config.attendance_geofence;
            this.state.attendance_geofence = attendance_geofence ? attendance_geofence : false;  
        }
    },
    async updateGeofenceAttendance(data) {
        var self = this;

        var employeeId= data.employeeId;
        var enteredPin = data.enteredPin;
        console.log(data)
        if (data && data.insideGeofences){
            const result = await this.rpc('manual_selection',
            {
                'token': this.props.token,
                'employee_id': employeeId,
                'pin_code': enteredPin,
            })
            if (result && result.attendance) {
                if (result.attendance.id && result.attendance_state == "checked_in"){
                    await this.rpc('update_checkin_geofence',{
                        'token': this.props.token,
                        'attendance_id':parseInt(result.attendance.id),
                        'geofences': data.insideGeofences,
                    })
                }
                else if(result.attendance.id && result.attendance_state == "checked_out"){
                    await this.rpc('update_checkout_geofence',{
                        'token': this.props.token,
                        'attendance_id':parseInt(result.attendance.id),
                        'geofences': data.insideGeofences,
                    })
                }
                this.employeeData = result
                this.switchDisplay('greet')
            }else{
                if (enteredPin){
                    this.displayNotification(_t("Wrong Pin"))
                }
            }
        }
    },
    async onManualSelection(employeeId, enteredPin){
        var companyId = this.props.companyId;
        if (this.state.attendance_geofence) {
            var geofenceIds = await this.rpc("/hr_attendance/get_geofences", {
                company_id : companyId,
                employee_id : employeeId,
            });

            this.dialog.add(AttendanceGeofenceDialog, {
                geofenceIds: geofenceIds,
                updateGeofenceAttendance: (attendance) => {
                    var input = {                         
                        'employeeId' : employeeId, 
                        'enteredPin' : enteredPin,
                    }
                    var data = Object.assign({}, input, attendance);
                    this.updateGeofenceAttendance(data);
                },
            });
        }else{
            const result = await this.rpc('manual_selection',
            {
                'token': this.props.token,
                'employee_id': employeeId,
                'pin_code': enteredPin
            })
            if (result && result.attendance) {
                this.employeeData = result
                this.switchDisplay('greet')
            }else{
                if (enteredPin){
                    this.displayNotification(_t("Wrong Pin"))
                }
            }
        }        
    },
});

