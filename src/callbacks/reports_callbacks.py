# src/callbacks/reports_callbacks.py

import dash
from dash import dcc, Output, Input, State
import datetime

from src.reporting.fallas_report import exportar_fallas_excel

def register_reports_callbacks(app):
    @app.callback(
        Output("report-custom-days-modal", "is_open"),
        [Input("download-report-custom", "n_clicks"),
         Input("report-modal-close-button", "n_clicks")],
        [State("report-custom-days-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_report_modal(n_open, n_close, is_open):
        """Abre y cierra el modal para el reporte personalizado."""
        if n_open or n_close:
            return not is_open
        return is_open

    @app.callback(
        [Output("report-days-input", "invalid"),
         Output("report-days-feedback", "children")],
        Input("report-days-input", "value"),
        prevent_initial_call=True
    )
    def validate_report_days_input(value):
        if value is None or not (1 <= value <= 365):
            return True, "Por favor, introduce un número entre 1 y 365."
        return False, ""

    @app.callback(
        Output("download-fallas-excel-dcc", "data"),
        [Input("download-report-7-days", "n_clicks"),
         Input("download-report-30-days", "n_clicks"),
         Input("report-modal-generate-button", "n_clicks")],
        [State("report-days-input", "value")],
        prevent_initial_call=True
    )
    def trigger_fallas_download(n7, n30, n_custom, custom_days):
        """Genera y envía el archivo Excel al cliente."""
        ctx = dash.callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        days_to_report = 0

        if trigger_id == "download-report-7-days": days_to_report = 7
        elif trigger_id == "download-report-30-days": days_to_report = 30
        elif trigger_id == "report-modal-generate-button":
            if custom_days and 1 <= custom_days <= 365: days_to_report = custom_days
            else: raise dash.exceptions.PreventUpdate

        if days_to_report <= 0: raise dash.exceptions.PreventUpdate

        filepath = exportar_fallas_excel(dias=days_to_report)
        return dcc.send_file(filepath, f"reporte_fallas_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx")