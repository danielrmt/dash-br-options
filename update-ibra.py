
import numpy as np
import pandas as pd


indice = 'IBRA'
url = 'http://bvmf.bmfbovespa.com.br/indices/ResumoCarteiraTeorica.aspx?' + \
    f'Indice={indice}'


data = pd.read_html(url)[0]
data.columns = ['ticker_acao', 'empresa', 'tipo', 'qtde', 'part']
data['part'] = data['part'] / 1000
data = data[data['part'] != 100]


data.to_csv('ibra.csv', index=False)
