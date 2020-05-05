

import numpy as np
import pandas as pd

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, ALL
import dash_table
from dash_table.Format import Format, Scheme, Sign

from layout_helpers import *


#
empresas = pd.read_csv('ativos.csv')
opcoes = pd.read_csv('opcoes.csv')
empresas['base_ticker'] = empresas['ticker_acao'].str[:4]
empresas = empresas[empresas['base_ticker'].isin(opcoes['base_ticker'])]
empresas = empresas.sort_values('part', ascending=False).drop_duplicates('base_ticker')
vencims = opcoes['vencimento'].sort_values().unique()

# APP INITIALIZATION
app = dash.Dash(
    __name__,
    external_stylesheets=["https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css"],
    external_scripts=[
        'https://code.jquery.com/jquery-3.4.1.slim.min.js',
        'https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js',
        'https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js'
    ]
    )
server = app.server


# TABLE
table = dash_table.DataTable(id='options_table', data=[], columns=[],
    style_as_list_view=True, style_header={'fontWeight': 'bold'})

# SIDEBAR
empresas_opt = [{'label': s, 'value': s} for s in empresas['ticker_acao']]
vencims_opt = [{'label': s, 'value': s} for s in vencims]
tipos = ['call', 'put', 'americano', 'europeu']
sidebar = html.Div([
    dcc.Dropdown(id='empresa', value='BOVA11', options=empresas_opt),
    dcc.Dropdown(id='vencim', value=vencims.min(), options=vencims_opt),
    dcc.Checklist(id='tipos', value=tipos,
        options=[{'label':s,'value':s} for s in tipos]),
    table
])




# MAIN GRID
grid = gen_grid([
    ['']
])


# LAYOUT
app.title = "Brazilian Options"
navbar = gen_navbar(app.title,
    {'Github': 'https://github.com/danielrmt/dash-br-options'})
hidden = html.Div(
    [html.Div([], id=s) for s in ['options_data']],
    style={'display': 'none'})
app.layout = html.Div([
    navbar,
    gen_sidebar_layout(sidebar, grid, 4, mainClass='container-fluid'),
    hidden])


# CALLBACKS
@app.callback(
    Output('options_data', 'children'),
    [Input('empresa', 'value'),
     Input('vencim', 'value'),
     Input('tipos','value')])
def update_data(empresa, vencim, tipos):
    df = opcoes[(opcoes['base_ticker'] == empresa[:4]) &
                (opcoes['tipo_opcao'].isin(tipos)) &
                (opcoes['tipo_exercicio'].str.lower().isin(tipos)) &
                (opcoes['vencimento'] == vencim)][['ticker_opcao', 'strike',
                                                   'tipo_opcao',
                                                   'tipo_exercicio']]
    return [df.to_json(date_format='iso', orient='split')]

#

numeric_fmt = Format(precision=1, scheme=Scheme.fixed, sign=Sign.parantheses)
@app.callback(
    [Output('options_table', 'data'),
     Output('options_table', 'columns')],
    [Input('options_data', 'children')])
def update_table(data):
    df = pd.read_json(data[0], orient='split')

    return df.to_dict('records'), \
        [{'name':str(s),'id':str(s),'type':'numeric',
         'format':numeric_fmt} for s in df.columns]

# ----
if __name__ == '__main__':
    app.run_server(debug=True)
