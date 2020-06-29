

import os
import requests
import urllib.request as ur
from zipfile import ZipFile
from io import BytesIO
import datetime
import json

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


def download_ativos(indice='IBRA'):
    url = 'http://bvmf.bmfbovespa.com.br/indices/ResumoCarteiraTeorica.aspx?' + \
        f'Indice={indice}'
    print(url)
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
    etfs['part'] = np.where(etfs['ticker_acao'] == 'BOVA11', 100, 0)
    etfs['tipo'] = 'ETF'

    return pd.concat([acoes, etfs])


def download_opcoes():
    s = requests.Session()

    # Extract file url from B3 website
    url0 = 'http://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/' + \
        'market-data/consultas/mercado-a-vista/opcoes/series-autorizadas/'
    # url = 'http://www.bmfbovespa.com.br/pt_br/servicos/market-data/' + \
    #     'consultas/mercado-a-vista/opcoes/series-autorizadas/'
    page = s.get(url0)
    soup = BeautifulSoup(page.text, 'html.parser')
    url = soup.find("a", string="Lista Completa de Séries Autorizadas").get('href')
    url = 'http://www.b3.com.br' + url
    # url = 'http://www.bmfbovespa.com.br/' + url
    print(url)

    h = {
        'Referer': url0,
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
    }
    r = s.get(url, headers=h)

    # Unzip
    with ZipFile(BytesIO(r.content), 'r') as zip_ref:
        zip_ref.extractall()

    if not os.path.exists('SI_D_SEDE.txt'):
        raise Exception('SI_D_SEDE.txt not found')
    else:
        # Wrangle data
        df = pd.read_csv('SI_D_SEDE.txt', '|', skiprows=1, header=None,
                        names=['x1', 'empresa', 'x2', 'tipo_opcao', 'x3', 'x4',
                                'ticker_empresa', 'tipo_acao', 'x5', 'x6', 'x7',
                                'x8', 'x9', 'ticker_opcao', 'x10',
                                'tipo_exercicio', 'strike', 'vencimento', 'x11'],
                        usecols=[3, 13, 15, 16, 17],
                        parse_dates=['vencimento'], infer_datetime_format=True)
        df['base_ticker'] = df['ticker_opcao'].str[:4]
        df['tipo_opcao'] = df['tipo_opcao'].replace({'OPCOES VENDA': 'put',
                                                    'OPCOES COMPRA': 'call'})
        df = df[df['tipo_opcao'].isin(['call', 'put'])]
        df['ticker_opcao'] = df['ticker_opcao'].str.strip()
        df['vencimento'] = pd.to_datetime(df['vencimento']).dt.strftime('%Y-%m-%d')
        return df


def last_selic():    
    data = datetime.datetime.now().strftime("%d/%m/%Y")
    url = f'https://www.bcb.gov.br/api/servico/sitebcb/bcdatasgs?serie=432&dataInicial={data}&dataFinal={data}'
    return json.loads(requests.get(url).text)['conteudo'][0]['valor']


def download_feriados():
    return pd.read_excel(
        'https://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls',
        skipfooter=9)[['Data']]


def get_quotes(tickers):
    url = 'http://bvmf.bmfbovespa.com.br/cotacoes2000/' + \
        'FormConsultaCotacoes.asp?strListaCodigos=' + '|'.join(tickers)
    page = requests.get(url)
    xml = ET.fromstring(page.text)
    df = pd.DataFrame([p.attrib for p in xml.findall('Papel')])
    df = df[['Codigo', 'Data', 'Ultimo']]
    df.columns = ['ticker', 'data', 'cotacao']
    df['cotacao'] = pd.to_numeric(df['cotacao'].str.replace(',','.'))
    return df


def cache_data(fn, fun):
    if os.path.exists(fn):
        print(f'{fn} exists, using cached version')
        return pd.read_csv(fn)
    else:
        print(f'{fn} does not exist, creating file')
        df = fun()
        df.to_csv(fn, index=False)
        return df
