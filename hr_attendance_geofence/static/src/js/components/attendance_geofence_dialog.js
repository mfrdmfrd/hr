/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { onMounted, onWillStart, useState, useRef, useEffect, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS, loadCSS } from "@web/core/assets";

export class AttendanceGeofenceDialog extends Component {
    setup() {
        this.title = _t("Attendance Geofence");        
        this.mapContainerRef = useRef("mapContainer");
        this.notificationService = useService('notification');
        this.rpc = useService("rpc");
        
        this.state = useState({
            olmap: null,
            geolocation: false,
            vectorLayer: false,
            geofenceObjects: [],
            okClassName: 'd-none',
        });

        useEffect(
            () => {
                this.state.olmap = new ol.Map({
                    layers: [
                        new ol.layer.Tile({
                            source: new ol.source.OSM(),
                        })],
                    view: new ol.View({
                        center: ol.proj.fromLonLat([0, 0]),
                        zoom: 0,
                    }),
                });
                this.state.olmap.setTarget(this.mapContainerRef.el);
                this.state.olmap.updateSize();
                if(this.state.olmap){
                    this.updateMap();
                }
            },
            () => []
        );
        useEffect(() => {
            
        });

        onWillStart(async () => {
            await loadCSS("/hr_attendance_geofence/static/src/js/lib/ol-6.12.0/ol.css");
            await loadCSS("/hr_attendance_geofence/static/src/js/lib/ol-ext/ol-ext.css");
            await loadJS("/hr_attendance_geofence/static/src/js/lib/ol-6.12.0/ol.js");
            await loadJS("/hr_attendance_geofence/static/src/js/lib/ol-ext/ol-ext.js");            
        });
        
        onMounted(async () => {
            this.onMounted();
        });
    }
    onMounted() {
        if(this.state.olmap){
            this.state.olmap.updateSize();
        }
    }
    updateMap(){
        if (this.state.olmap){
            this.addLayerVector();
        }
    }
    addLayerVector(){
        var self = this;
        if (window.location.protocol == 'https:'){
            var options = {
                enableHighAccuracy: true,
                maximumAge: 30000,
                timeout: 27000
            };
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(successCallback, errorCallback, options);
            }else {
                self.state.geolocation = false;
            }

            function successCallback(position) { 
                self.latitude = position.coords.latitude;
                self.longitude = position.coords.longitude;
                if(self.state.olmap){
                    var layersToRemove = [];
                    self.state.olmap.getLayers().forEach(layer => {
                        if (layer.get('name') != undefined && layer.get('name') === 'vectorSource') {
                            layersToRemove.push(layer);
                        }
                    });

                    var len = layersToRemove.length;
                    for(var i = 0; i < len; i++) {
                        self.state.olmap.removeLayer(layersToRemove[i]);
                    }

                    const coords = [position.coords.longitude, position.coords.latitude];
                    const accuracy = ol.geom.Polygon.circular(coords, position.coords.accuracy);

                    self.state.vectorLayer = new ol.layer.Vector({
                        source: new ol.source.Vector({
                            features: [
                                new ol.Feature(
                                    accuracy.transform('EPSG:4326', self.state.olmap.getView().getProjection())
                                ),
                                new ol.Feature({
                                    geometry: new ol.geom.Point(ol.proj.fromLonLat(coords))
                                })
                            ]
                        })
                    });
                    self.state.vectorLayer.set('name', 'vectorSource');
                    self.state.olmap.addLayer(self.state.vectorLayer);
                    var extent = self.state.vectorLayer.getSource().getExtent();
                    if(extent){
                        self.state.olmap.getView().fit(extent, {duration: 100, maxZoom:6});   
                    }
                    self.state.olmap.updateSize();

                    self.state.okClassName = '';
                }
            }

            function errorCallback(err) {
                switch(err.code) {
                    case err.PERMISSION_DENIED:
                    console.log("The request for geolocation was refused by the user.");
                    break;
                    case err.POSITION_UNAVAILABLE:
                        console.log("There is no information about the location available.");
                    break;
                    case err.TIMEOUT:
                        console.log("The request for the user's location was unsuccessful.");
                    break;
                    case err.UNKNOWN_ERROR:
                        console.log("An unidentified error has occurred.");
                    break;
                }
            }
        }
    }
    close() {
        this.props.close && this.props.close();
    }
    async onClickConfirm(ev){
        ev.preventDefault();
        ev.stopPropagation();

        var self = this;
        var insidePolygon = false;
        var insideGeofences = []
        if(self.state.olmap){
            for (let i = 0; i < self.props.geofenceIds.length; i++) {
                var path = self.props.geofenceIds[i].overlay_paths;
                var value = JSON.parse(path);
                if (Object.keys(value).length > 0) {                                                                    
                    let coords = ol.proj.fromLonLat([self.longitude,self.latitude]);
                    var features = new ol.format.GeoJSON().readFeatures(value);                        
                    var geometry = features[0].getGeometry();
                    var insidePolygon = geometry.intersectsCoordinate(coords);
                    if (insidePolygon === true) {
                        insideGeofences.push(self.props.geofenceIds[i].id);
                    }
                }
            }
            
            if (insideGeofences.length > 0){
                var position = {
                    latitude: self.longitude,
                    longitude: self.latitude,
                }
                await self.props.updateGeofenceAttendance({
                    position: position,
                    insideGeofences: insideGeofences,
                });
                self.props.close();
            }else{
                self.notificationService.add("You haven't entered any of the geofence zones.", {
                    title: _t("Attenance Geofence"),
                    type: "danger",
                    sticky: true,
                });
            }
        }
    }
}
AttendanceGeofenceDialog.components = { Dialog };
AttendanceGeofenceDialog.template = "hr_attendance_geofence.AttendanceGeofenceDialog";
AttendanceGeofenceDialog.defaultProps = {};
AttendanceGeofenceDialog.props = {
    geofenceIds: { type: Object },
}