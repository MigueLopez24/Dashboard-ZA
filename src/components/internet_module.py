# src/components/internet_module.py

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from ..components.card_header import crear_header_modulo

def crear_layout_internet_speed(velocidad_descarga, velocidad_carga=None, ping=None, remotos=None, empresariales=None):
    header = crear_header_modulo("INTERNET", '/assets/icons/velocidad.png')
    
    # Crear el gráfico de medidor de velocidad
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = velocidad_descarga,
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'shape': "angular",
            'axis': {'range': [0, 200], 'tickwidth': 1, 'tickcolor': "#444"},
            'bar': {'color': "#590ebb", 'thickness': 0.3},
            'bgcolor': "black",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 200], 'color': '#0EC1E6'},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            },
            'bordercolor': "#444"
        },
        name="Velocidad (Mbps)"
    ))

    fig.update_layout(
        height=75,    
        width=200,    
        margin={'l':5, 'r':5, 't':0, 'b':0},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "white"},
    )
    
    if all(arg is not None for arg in [velocidad_carga, ping, remotos, empresariales]):
        speed_layout = html.Div(
            [
                html.Div(
                    dcc.Graph(figure=fig, config={'displayModeBar': False}),
                    className="d-flex justify-content-center w-100" 
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Img(src='/assets/icons/ping.png', className="internet-speed-icon"),
                                        html.Span(f"{ping} ms", className="internet-speed-value"),
                                    ],
                                    className="d-flex align-items-center"
                                ),
                                html.Div(
                                    [
                                        html.Img(src='/assets/icons/download.png', className="internet-speed-icon"),
                                        html.Span(f"{velocidad_descarga} Mbps", className="internet-speed-value"),
                                    ],
                                    className="d-flex align-items-center"
                                ),
                                html.Div(
                                    [
                                        html.Img(src='/assets/icons/upload.png', className="internet-speed-icon"),
                                        html.Span(f"{velocidad_carga} Mbps", className="internet-speed-value"),
                                    ],
                                    className="d-flex align-items-center"
                                ),
                            ],
                            className="d-flex justify-content-around my-2 w-100"
                        ),
                        html.Div(
                            [
                                html.Div([
                                    html.Img(src='/assets/icons/remotos.png', className="internet-users-icon"),
                                    html.Span(f"{remotos} remotos", className="internet-users-value"),
                                ], className="d-flex align-items-center mb-1"),
                                html.Div([
                                    html.Img(src='/assets/icons/dispositivos.png', className="internet-users-icon"),
                                    html.Span(f"{empresariales} empresariales", className="internet-users-value"),
                                ], className="d-flex align-items-center mb-1"),
                            ], className="p-1 bg-dark rounded-3 mx-auto"
                        )
                    ],
                    className="d-flex flex-column align-items-center w-100"
                )
            ],
            className="d-flex flex-column align-items-center p-1"
        )
        return {"header": header, "body": speed_layout, "figure": fig}
    
    return {"figure": fig}