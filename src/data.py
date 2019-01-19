import pandas as pd
import json
import requests
import config
import datetime
import os
import tools
from urllib.parse import quote

sample_query = {
  "line_ou_2013": "date,line,margin,ou margin,team,total @ date>20130101"
}

def querySDQL(league, query):
  """Takes league and SDQL compliant query, returns dataframe containing result
  """
  query = quote(query)
  url = "http://api.sportsdatabase.com/{0}/query.json?sdql=".format(league)
  api = "&output=json&api_key=guest"
  headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

  r = requests.get(url + query + api, headers=headers)
  parse = r.text.split("(")[1].split(")")[0] 
  output = json.loads(parse.replace("\t","").replace("\'", '\"'))
  columns = output['headers']
  data = output['groups'][0]['columns']
  data_dict = {columns[i]: data[i] for i in range(len(columns))}
  return pd.DataFrame(data_dict)
