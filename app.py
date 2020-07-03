

import numpy as np
import pandas as pd
from datetime import date

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
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
feriados = list(cache_data('feriados.csv', download_feriados)['Data'])
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
    external_stylesheets=[dbc.themes.BOOTSTRAP]
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
      dcc.Input(id='posicao_ativo', type='number', value=0,
                className='form-control')]],
    [dbc.Checklist(id='tipos', value=tipos, inline=True, switch=True,
        options=[{'label':s,'value':s} for s in tipos])],
    [dbc.Spinner(table)]
])
# CARDS
cards = html.Div([
    gen_card('', id='quote_card', title='Cotação do ativo'),
    gen_card(selic, id='selic_card', title='SELIC'),
    gen_card('', id='dias_vencim', title='Dias para vencimento')
], className='row')


# MAIN GRID
grid = gen_grid([
    [dbc.RadioItems(
        options=[{'label': x,'value': x} for x in ['R$', '%']],
        id='payoff_unit', value='R$', persistence=True, inline=True
    )],
    [spinner_graph(id='payoff_plot'),
     spinner_graph(id='simulation_plot')]
])


# LAYOUT
app.title = "Payoff de Opções"
navbar = gen_navbar(app.title,
    {})
hidden = html.Div(
    [html.Div([], id=s) for s in ['options_data']],
    style={'display': 'none'})
app.layout = html.Div([
    navbar,
    html.Div([
        cards,
        sidebar,
        grid,
    ], className='container'),
    html.Footer([
        html.Div([
            'Este aplicativo tem objetivo exclusivamente educacional e ' + \
            'todos os dados possuem caráter informativo. Não nos ' + \
            'responsabilizamos pelas decisões e caminhos tomados tomados ' + \
            'pelo usuário a partir da análise das informações aqui ' + \
            'disponibilizadas.'
        ], className='container')
    ], className='footer text-muted'),
    hidden
])


# CALLBACKS
@app.callback(
    Output('dias_vencim', 'children'),
    [Input('vencim', 'value')])
def update_wdays(vencim):
    return np.busday_count(np.datetime64('today', 'D'), vencim,
                           holidays=feriados)


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
    df = pd.merge(df, quotes, on='ticker', how='left')
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
    medianvol = df['Vol'].median()
    cotacao_bs = black_scholes(cotacao_ativo, df['strike'], float(selic),
        medianvol, dias_vencim, df['tipo_opcao'])['price']
    df['cotacao'] = np.where(df['cotacao'].isnull(), cotacao_bs, df['cotacao'])

    df = df[df['posicao'] != 0]
    custo = np.sum(df['posicao'] * df['cotacao']) + posicao_ativo*cotacao_ativo
    if df.shape[0] == 0:
        payoff = pd.DataFrame(
            strikes * posicao_ativo - custo,
            index=strikes, columns=['payoff'])
    else:
        payoff = pd.DataFrame(index=strikes, columns=df['ticker']).reset_index()
        payoff = payoff.melt('index')
        payoff = pd.merge(payoff, df, how='left')
        payoff['Vol'] = payoff['Vol'].fillna(medianvol)
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
        xlab = 'Variação'
    else:
        xlab = 'Cotação'
    fig = px.line(payoff, x='index', y='value', color='variable',
        title='Payoff no vencimento',
        labels={'index':f'{xlab} do ativo ({payoff_unit})',
                'value': f'Payoff ({payoff_unit})',
                'variable':''})
    if payoff_unit == 'R$':
        fig.add_shape(type='line', line=dict(color='#999999', dash='dot'),
            x0=cotacao_ativo, y0=payoff['value'].min()-1,
            x1=cotacao_ativo, y1=payoff['value'].max()+1)
    return fig


@app.callback(
    Output('simulation_plot', 'figure'),
    [Input('options_table', 'data'),
     Input('payoff_unit', 'value'),
     Input('quote_card', 'children'),
     Input('posicao_ativo', 'value'),
     Input('dias_vencim', 'children'),
     Input('vencim', 'value')]
)
def update_montecarlo(data, payoff_unit, cotacao_ativo, posicao_ativo,
                  dias_vencim, vencim):
    cotacao_ativo = cotacao_ativo[0]
    df = pd.DataFrame(data)
    nsims = 100
    vol = df['Vol'].max()
    df['Vol'] = df['Vol'].fillna(df['Vol'].median())

    cotacao_bs = black_scholes(cotacao_ativo, df['strike'], float(selic),
        vol, dias_vencim, df['tipo_opcao'])['price']
    df['cotacao'] = np.where(df['cotacao'].isnull(), cotacao_bs, df['cotacao'])
    
    custo = np.sum(df['posicao'] * df['cotacao']) + posicao_ativo*cotacao_ativo

    if (df['posicao'].min() == 0) and (df['posicao'].max() == 0) and \
        (posicao_ativo == 0):
        return {}

    sim = pd.DataFrame(
        np.random.normal(0, np.sqrt(vol**2 / 252), (dias_vencim, nsims)),
        index=range(dias_vencim, 0, -1), columns=range(nsims)
    ).cumsum().reset_index().melt('index', var_name='sim', value_name='logreturn')
    sim['cotacao'] = cotacao_ativo * np.exp(sim['logreturn'])

    sim['payoff'] = sim['cotacao'] * posicao_ativo - custo
    for ticker in df['ticker'][df['posicao'] != 0]:
        row = df[df['ticker'] == ticker]
        v_op = black_scholes(sim['cotacao'], row['strike'].values[0],
            float(selic), row['Vol'].values[0],
            sim['index'], row['tipo_opcao'].values[0])
        sim['payoff'] = sim['payoff'] + v_op['price'] * row['posicao'].values[0]

    if payoff_unit == '%':
        sim['payoff'] = 100 * sim['payoff'] / custo

    sim['data'] = np.busday_offset(vencim, - sim['index'], 'backward',
        holidays=feriados)

    fig = px.line(sim, x='data', y='payoff', line_group='sim',
        title='Simulações',
        labels={'data': '', 'payoff': f'Payoff ({payoff_unit})'})
    fig.update_traces(line={'color': 'rgba(153,153,153,0.5)'})

    return fig

# ----
if __name__ == '__main__':
    app.run_server(debug=True)
