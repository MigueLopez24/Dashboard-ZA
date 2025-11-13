import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone

def _to_local_datetime(fecha):
    if isinstance(fecha, str):
        try:
            fecha = datetime.fromisoformat(fecha)
        except Exception:
            return fecha
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone()

def create_internet_history_figure(history_data: dict) -> go.Figure:
    fig = go.Figure()
    if (isinstance(history_data, dict) and
        "error" not in history_data and
        history_data.get('fechas') and
        history_data.get('descarga') and
        history_data.get('carga')):
        fechas_locales = [_to_local_datetime(f) for f in history_data['fechas']]
        fig.add_trace(go.Scatter(x=fechas_locales, y=history_data['descarga'], mode='lines', name='Descarga (Mbps)', line_color='#56C0BD'))
        fig.add_trace(go.Scatter(x=fechas_locales, y=history_data['carga'], mode='lines', name='Carga (Mbps)', line_color="#BF71FF"))
        fig.update_layout(
            title_text='',
            template='plotly_dark', xaxis_title="Fecha y Hora",
            yaxis=dict(title="Velocidad (Mbps)", range=[0, 200], fixedrange=True),
            legend=dict(font=dict(size=8), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=9),
            margin={'l': 30, 'r': 5, 't': 10, 'b': 10},
        )
    return fig

def create_faults_pie_chart(fallas_data: dict) -> go.Figure:
    fig = go.Figure()
    if "error" not in fallas_data and fallas_data.get('labels'):
        fig = px.pie(names=fallas_data['labels'], values=fallas_data['fallas'], hole=0.4,
                     color_discrete_sequence=px.colors.diverging.Picnic, labels={'names': 'Dispositivo'})
        fig.update_traces(textposition='inside', textinfo='percent', textfont_size=12, insidetextorientation='radial')
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font={'color': 'white', 'size': 12},
            showlegend=True,
            legend=dict(font=dict(size=12), orientation="v", yanchor="top", y=0.95, xanchor="left", x=1.01),
            margin={'l': 20, 'r': 5, 't': 10, 'b': 10},
            width=300, height=150
        )
    return fig

def create_storyline_figure(storyline_data: dict) -> go.Figure:
    fig = go.Figure()
    if (isinstance(storyline_data, dict) and "error" not in storyline_data and storyline_data.get('fechas') and storyline_data.get('sitios')):
        fechas_locales = [_to_local_datetime(f) for f in storyline_data['fechas']]
        color_palette = px.colors.qualitative.Plotly
        jitter_amount = 0.04
        sitios_items = list(storyline_data['sitios'].items())
        num_sitios = len(sitios_items)
        for idx, (sitio, estados) in enumerate(sitios_items):
            offset = (idx - (num_sitios - 1) / 2) * jitter_amount
            y_values_with_offset = [estado + offset for estado in estados]
            hover_texts = ['Activo' if e == 1 else 'Caído' for e in estados]
            fig.add_trace(go.Scatter(
                x=fechas_locales, y=y_values_with_offset, mode='lines+markers',
                name=sitio, customdata=hover_texts,
                line=dict(color=color_palette[idx % len(color_palette)], width=2, shape='hv'),
                marker=dict(size=6),
                hovertemplate='<b>%{fullData.name}</b><br>Estado: %{customdata}<br>Fecha: %{x|%d/%m/%Y %H:%M:%S}<extra></extra>'
            ))
        fig.update_layout(
            title_text='',
            template='plotly_dark', xaxis_title="Fecha y Hora",
            yaxis=dict(title="Estado", tickvals=[0, 1], ticktext=["Caído", "Activo"], range=[-0.5, 1.5]),
            legend=dict(font=dict(size=8), orientation="h", yanchor="top", y=1.10, xanchor="right", x=1),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=9),
            margin={'l': 20, 'r': 5, 't': 30, 'b': 30},
            height=200
        )
    return fig