/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { AttendanceGeofenceDialog } from "./attendance_geofence_dialog"
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(ActivityMenu.prototype, {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");
        this.notificationService = useService("notification");
        this.company = useService("company");
    },
    async searchReadEmployee(){
        await super.searchReadEmployee();
        const attendance_geofence = this.employee.attendance_geofence;
        this.state.attendance_geofence = attendance_geofence ? attendance_geofence : false;        
    },
    async updateGeofenceAttendance({ attendance }) {
        var self = this;
        if (attendance){
            if (attendance && attendance.insideGeofences){
                navigator.geolocation.getCurrentPosition(
                    async ({coords: {latitude, longitude}}) => {
                        await self.rpc("/hr_attendance/systray_check_in_out", {
                            latitude,
                            longitude
                        }).then(async function(data){                        
                            if (data.attendance.id && data.attendance_state == "checked_in"){
                                await self.rpc("/web/dataset/call_kw/hr.attendance/write", {
                                    model: "hr.attendance",
                                    method: "write",
                                    args: [parseInt(data.attendance.id), {
                                        'check_in_geofence_ids': [[6, 0, attendance.insideGeofences]],
                                    }],
                                    kwargs: {},
                                })
                            }
                            else if(data.attendance.id && data.attendance_state == "checked_out"){
                                await self.rpc("/web/dataset/call_kw/hr.attendance/write", {
                                    model: "hr.attendance",
                                    method: "write",
                                    args: [parseInt(data.attendance.id), {
                                        'check_out_geofence_ids': [[6, 0, attendance.insideGeofences]],
                                    }],
                                    kwargs: {},
                                })
                            }                        
                        })
                        await self.searchReadEmployee()
                    },
                    async err => {
                        await self.rpc("/hr_attendance/systray_check_in_out")
                        await self.searchReadEmployee()
                    }
                )
            }
        }
    },
    async signInOut() {
        if (this.state.attendance_geofence) {
            if (window.location.protocol == 'https:') {

                var geofenceIds = await this.rpc("/hr_attendance/get_geofences", {
                    company_id : this.company.currentCompany.id,
                    employee_id : this.employee.id,
                });

                this.dialog.add(AttendanceGeofenceDialog, {
                    geofenceIds: geofenceIds,
                    updateGeofenceAttendance: (attendance) => {
                        this.updateGeofenceAttendance({attendance});
                    }
                });
            }else{
                this.notificationService.add("GEOLOCATION MAY ONLY WORKS WITH HTTPS CONNECTIONS", {
                    title: _t("Attenance Geofence"),
                    type: "danger",
                    sticky: true,
                });
            }
        } else {
            navigator.geolocation.getCurrentPosition(
                async ({coords: {latitude, longitude}}) => {
                    await this.rpc("/hr_attendance/systray_check_in_out", {
                        latitude,
                        longitude
                    })
                    await this.searchReadEmployee()
                },
                async err => {
                    await this.rpc("/hr_attendance/systray_check_in_out")
                    await this.searchReadEmployee()
                }
            )
        }
    }
});
export default ActivityMenu;