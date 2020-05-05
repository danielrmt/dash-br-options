#!/usr/bin/env python3


import os
import requests
from bs4 import BeautifulSoup
import urllib.request as ur
from zipfile import ZipFile
import pandas as pd
import numpy as np


# Extract file url from B3 website
url = 'http://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/' + \
    'market-data/consultas/mercado-a-vista/opcoes/series-autorizadas/'
page = requests.get(url)
soup = BeautifulSoup(page.text, 'html.parser')
url = soup.find("a", string="Lista Completa de Séries Autorizadas").get('href')
url = 'http://www.b3.com.br' + url


# Unzip
filehandle, _ = ur.urlretrieve(url)
with ZipFile(filehandle, 'r') as zip_ref:
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

    # Save
    df.to_csv('opcoes.csv', index=False)
