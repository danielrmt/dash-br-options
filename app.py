

import numpy as np
import pandas as pd

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, ALL
import dash_table
from dash_table.Format import Format, Scheme, Sign

from layout_helpers import *
from data_helpers import *


#
selic = last_selic()
empresas = cache_data('ativos.csv', download_ativos)
opcoes = cache_data('opcoes.csv', download_opcoes)
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
sidebar = gen_grid([
    [['Ativo',
      dcc.Dropdown(id='empresa', value='BOVA11', clearable=False,
                   options=empresas_opt)],
     ['Vencimento', dcc.Dropdown(id='vencim', clearable=False,
                                 value=vencims.min(), options=vencims_opt)]],
    [dcc.Checklist(id='tipos', value=tipos,
        options=[{'label':s,'value':s} for s in tipos])],
    [table]
])


# MAIN GRID
grid = gen_grid([
    [gen_card('', id='quote_card', title='Cotação do ativo'),
     gen_card(selic, id='selic_card', title='SELIC'),
     gen_card('', id='dias_vencim', title='Dias para vencimento')],
    [dcc.Graph(id='payoff_plot')]
])


# LAYOUT
app.title = "Brazilian Options"
navbar = gen_navbar(app.title,
    {})
hidden = html.Div(
    [html.Div([], id=s) for s in ['options_data']],
    style={'display': 'none'})
app.layout = html.Div([
    navbar,
    gen_sidebar_layout(sidebar, grid, 6, mainClass='container-fluid'),
    hidden])


# CALLBACKS
@app.callback(
    Output('dias_vencim', 'children'),
    [Input('vencim', 'value')])
def update_wdays(vencim):
    return np.busday_count(np.datetime64('today', 'D'), vencim)


@app.callback(
    Output('quote_card', 'children'),
    [Input('empresa', 'value')])
def update_quote(empresa):
    return get_quotes([empresa]).tail(1)['cotacao'].values


@app.callback(
    Output('options_data', 'children'),
    [Input('empresa', 'value'),
     Input('vencim', 'value'),
     Input('tipos', 'value'),
     Input('quote_card', 'children')])
def update_data(empresa, vencim, tipos, cotacao_ativo):
    df = opcoes[(opcoes['base_ticker'] == empresa[:4]) &
                (opcoes['tipo_opcao'].isin(tipos)) &
                (opcoes['tipo_exercicio'].str.lower().isin(tipos)) &
                (opcoes['vencimento'] == vencim)]
    cotacao_ativo = cotacao_ativo[0]
    df['diffstrike'] = np.abs(cotacao_ativo - df['strike'])
    df.sort_values('diffstrike', inplace=True)
    df['VI'] = np.where(df['tipo_opcao'] == 'call',
                        cotacao_ativo - df['strike'],
                        df['strike'] - cotacao_ativo)
    df['VI'] = np.where(df['VI'] < 0, 0, df['VI'])
    df = df.head(20).rename(columns={'ticker_opcao':'ticker'})

    quotes = get_quotes(df['ticker'].values)
    df = pd.merge(df, quotes, on='ticker')
    df['VE'] = df['cotacao'] - df['VI']

    df = df[['ticker', 'strike', 'tipo_opcao', 'tipo_exercicio', 'cotacao',
             'VI', 'VE']]
    return [df.to_json(date_format='iso', orient='split')]

#
int_fmt = Format(precision=0, scheme=Scheme.fixed, sign=Sign.parantheses)
numeric_fmt = Format(precision=2, scheme=Scheme.fixed, sign=Sign.parantheses)
@app.callback(
    [Output('options_table', 'data'),
     Output('options_table', 'columns')],
    [Input('options_data', 'children')])
def update_table(data):
    df = pd.read_json(data[0], orient='split')
    df['posicao'] = 0
    return df.to_dict('records'), \
        [{'name': str(s), 'id': str(s), 'type': 'numeric',
         'format': numeric_fmt if s != 'posicao' else int_fmt,
         'editable': s == 'posicao'} for s in df.columns]


@app.callback(
    Output('payoff_plot', 'figure'),
    [Input('options_table', 'data')]
)
def update_payoff(data):
    df = pd.DataFrame(data)
    strikes = np.arange(df['strike'].min()-1, df['strike'].max()+1, 0.01)
    df = df[df['posicao'] != 0]
    custo = np.sum(df['posicao'] * df['cotacao'])
    if df.shape[0] == 0:
        return {}
    
    payoff = pd.DataFrame(index=strikes, columns=df['ticker']).reset_index()
    payoff = payoff.melt('index')
    payoff = pd.merge(payoff, df)
    payoff['payoff'] = 0
    payoff['payoff'] = np.where(payoff['tipo_opcao'] == 'call', 
                                payoff['index'] - payoff['strike'],
                                payoff['payoff'])
    payoff['payoff'] = np.where(payoff['tipo_opcao'] == 'put', 
                                payoff['strike'] - payoff['index'],
                                payoff['payoff'])
    payoff['payoff'] = np.where(payoff['payoff'] < 0, 0, payoff['payoff'])
    payoff['payoff'] = payoff['payoff'] * payoff['posicao'].fillna(0)
    payoff = payoff.groupby('index')['payoff'].sum() - custo

    return {'data':[{'x':payoff.index, 'y':payoff.values}]}

# ----
if __name__ == '__main__':
    app.run_server(debug=True)
