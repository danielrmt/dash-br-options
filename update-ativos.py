
import numpy as np
import pandas as pd


indice = 'IBRA'
url = 'http://bvmf.bmfbovespa.com.br/indices/ResumoCarteiraTeorica.aspx?' + \
    f'Indice={indice}'
acoes = pd.read_html(url)[0]
acoes.columns = ['ticker_acao', 'empresa', 'tipo', 'qtde', 'part']
acoes['part'] = acoes['part'] / 1000
acoes = acoes[acoes['part'] != 100]


url = 'http://bvmf.bmfbovespa.com.br/etf/fundo-de-indice.aspx?idioma=pt-br' + \
    '&aba=tabETFsRendaVariavel'
etfs = pd.read_html(url)[0]
etfs.columns = ['a', 'empresa', 'b', 'ticker_acao']
etfs = etfs[['empresa', 'ticker_acao']]
etfs['ticker_acao'] = etfs['ticker_acao'] + '11'
etfs['part'] = 0
etfs['tipo'] = 'ETF'

data = pd.concat([acoes, etfs])

data.to_csv('ativos.csv', index=False)
