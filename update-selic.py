#!/usr/bin/env python3

import datetime
import json
import requests


data = datetime.datetime.now().strftime("%d/%m/%Y")

url = f'https://www.bcb.gov.br/api/servico/sitebcb/bcdatasgs?serie=432&dataInicial={data}&dataFinal={data}'

selic = json.loads(requests.get(url).text)['conteudo'][0]['valor']

f = open('selic.txt', 'w')
f.write(selic)
f.close()
