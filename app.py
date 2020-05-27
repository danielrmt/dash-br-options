

import numpy as np
import pandas as pd
from datetime import date

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, ALL
import dash_table
from dash_table.Format import Format, Scheme, Sign

import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

from layout_helpers import *
from data_helpers import *
from finance_helpers import *


#
pio.templates["custom"] = go.layout.Template(
    layout=go.Layout(
        margin=dict(l=50, r=20, t=40, b=40),
        legend=dict(orientation='h'),
        colorway=["#E69F00", "#56B4E9", "#009E73", "#F0E442", 
                  "#0072B2", "#D55E00", "#CC79A7", "#999999"]
    )
)
pio.templates.default = 'custom'


#
selic = last_selic()
feriados = cache_data('feriados.csv', download_feriados)['Data']
empresas = cache_data('ativos.csv', download_ativos)
opcoes = cache_data('opcoes.csv', download_opcoes)
opcoes = opcoes[pd.to_datetime(opcoes['vencimento']) > pd.to_datetime(date.today())]
tickers_proxvenc = opcoes['base_ticker'][opcoes['vencimento'] ==
                                         opcoes['vencimento'].min()].unique()
empresas['base_ticker'] = empresas['ticker_acao'].str[:4]
empresas = empresas[empresas['base_ticker'].isin(tickers_proxvenc)]
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
tipos = ['call', 'put', 'americano', 'europeu', 'ITM', 'OTM', 'ATM']
sidebar = gen_grid([
    [['Ativo',
      dcc.Dropdown(id='empresa', value='BOVA11', clearable=False,
                   options=empresas_opt, persistence=True)],
     ['Vencimento', dcc.Dropdown(id='vencim', clearable=False,
                                 value=vencims.min(), options=vencims_opt)],
     ['Posição no ativo',
      dcc.Input(id='posicao_ativo', type='number', value=1,
                className='form-control')]],
    [dcc.Checklist(id='tipos', value=tipos,
        className='form-group', 
        labelClassName='form-check-label form-check form-check-inline',
        inputClassName='form-check-input',
        options=[{'label':s,'value':s} for s in tipos])],
    [table]
])


# MAIN GRID
grid = gen_grid([
    [gen_card('', id='quote_card', title='Cotação do ativo'),
     gen_card(selic, id='selic_card', title='SELIC'),
     gen_card('', id='dias_vencim', title='Dias para vencimento')],
    [html.Div('Este aplicativo foi criado com propósito exclusivamente ' + 
              'educacional. Não nos responsabilizamos por decisões de ' +
              'investimento tomadas pelo usuário.',
        className='alert alert-danger', role='alert')],
    [dcc.RadioItems(
        options=[{'label': x,'value': x} for x in ['R$', '%']],
        id='payoff_unit', value='R$', persistence=True,
        className='form-check form-check-inline',
        inputClassName='form-check-input form-check-inline',
        labelClassName='form-check-label form-check-inline'
    )],
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
    gen_sidebar_layout(sidebar, grid, 8, mainClass='container-fluid'),
    hidden])


# CALLBACKS
@app.callback(
    Output('dias_vencim', 'children'),
    [Input('vencim', 'value')])
def update_wdays(vencim):
    return np.busday_count(np.datetime64('today', 'D'), vencim,
                           holidays=feriados) - 1


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
     Input('quote_card', 'children'),
     Input('dias_vencim', 'children')])
def update_data(empresa, vencim, tipos, cotacao_ativo, dias_vencim):
    df = opcoes[(opcoes['base_ticker'] == empresa[:4]) &
                (opcoes['tipo_opcao'].isin(tipos)) &
                (opcoes['tipo_exercicio'].str.lower().isin(tipos)) &
                (opcoes['vencimento'] == vencim)]
    cotacao_ativo = cotacao_ativo[0]
    dias_vencim = int(dias_vencim)
    df['diffstrike'] = np.abs(cotacao_ativo - df['strike'])
    df.sort_values('diffstrike', inplace=True)
    df['VI'] = np.where(df['tipo_opcao'] == 'call',
                        cotacao_ativo - df['strike'],
                        df['strike'] - cotacao_ativo)
    df['VI'] = np.where(df['VI'] < 0, 0, df['VI'])

    df['money'] = np.where(df['VI'] > 0, 'ITM', 'OTM')
    df['money'] = np.where(df['diffstrike'] <= 0.5, 'ATM', df['money'])
    df = df[df['money'].isin(tipos)]

    df = df.head(20).rename(columns={'ticker_opcao':'ticker'})

    quotes = get_quotes(df['ticker'].values)
    df = pd.merge(df, quotes, on='ticker')
    df['VE'] = df['cotacao'] - df['VI']

    # Calculate implied volatility
    df['Vol'] = df.apply(
        lambda x: implied_vol(x['cotacao'], cotacao_ativo,
        x['strike'], float(selic), dias_vencim, x['tipo_opcao']),
        axis=1)
    # Calculate greeks
    gregas = black_scholes(cotacao_ativo, df['strike'], float(selic),
            df['Vol'], dias_vencim, df['tipo_opcao'])[
                ['delta','gamma','vega','theta','rho']
            ]
    df = pd.concat([df, gregas], axis=1)

    df = df[['ticker', 'strike', 'tipo_opcao', 'tipo_exercicio', 'money',
             'cotacao', 'VI', 'VE', 'Vol', 'delta', 'gamma', 'vega', 'theta', 'rho']]
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
        [{'name': str(s).replace('_', ' '), 'id': str(s), 'type': 'numeric',
          'format': numeric_fmt if s != 'posicao' else int_fmt,
          'editable': s == 'posicao'} for s in df.columns]


@app.callback(
    Output('payoff_plot', 'figure'),
    [Input('options_table', 'data'),
     Input('payoff_unit', 'value'),
     Input('quote_card', 'children'),
     Input('posicao_ativo', 'value'),
     Input('dias_vencim', 'children')]
)
def update_payoff(data, payoff_unit, cotacao_ativo, posicao_ativo, dias_vencim):
    cotacao_ativo = cotacao_ativo[0]
    df = pd.DataFrame(data)
    cot_range = df['cotacao'].max()*2 + 1
    strikes = np.arange(df['strike'].min()-cot_range, 
                        df['strike'].max()+cot_range, 0.01)
    df = df[df['posicao'] != 0]
    custo = np.sum(df['posicao'] * df['cotacao']) + posicao_ativo*cotacao_ativo
    if df.shape[0] == 0:
        payoff = pd.DataFrame(
            strikes * posicao_ativo - custo,
            index=strikes, columns=['payoff'])
    else:
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

        payoff['tomorrow']  = black_scholes(payoff['index'], payoff['strike'],
            float(selic), payoff['Vol'], dias_vencim - 1,
            payoff['tipo_opcao'])['price']
        payoff['tomorrow'] = payoff['tomorrow'] * payoff['posicao'].fillna(0)

        payoff = payoff.groupby('index')[['payoff', 'tomorrow']].sum()
        x = posicao_ativo * payoff.index - custo
        payoff['payoff'] = payoff ['payoff'] + x
        payoff['tomorrow'] = payoff ['tomorrow'] + x
    payoff = payoff.rename(columns={'payoff':'vencimento', 'tomorrow':'amanhã'})
    payoff = payoff.reset_index().melt('index')
    if payoff_unit == '%':
        payoff['value'] = 100 * (payoff['value'] / custo)
        payoff['index'] = 100 * (payoff['index'] / cotacao_ativo - 1)
        labs = {'index':'Variação do ativo (%)',
                'value': 'Payoff (%)',
                'variable':''}
    else:
        labs = {'index':'Cotação do ativo (R$)',
                'value': 'Payoff (R$)',
                'variable':''}
    fig = px.line(payoff, x='index', y='value', color='variable',
        title='Payoff no vencimento', labels=labs)
    if payoff_unit == 'R$':
        fig.add_shape(type='line', line=dict(color='#999999', dash='dot'),
            x0=cotacao_ativo, y0=payoff['value'].min()-1,
            x1=cotacao_ativo, y1=payoff['value'].max()+1)
    return fig

# ----
if __name__ == '__main__':
    app.run_server(debug=True)
