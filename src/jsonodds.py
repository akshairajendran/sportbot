import tools
import datetime
import requests
import json
import config
import numpy as np
import pandas as pd

class JSONOdds():
  def __init__(self):
    self.query_log = "../logs/jsonodds.log"
    self.query_per_month = 900
    self.query_df = "../logs/jsonodds.csv"

    self.league_enum = {
    1:"nba",
    2:"ncaab",
    4:"nfl",
    5:"nhl",
    }

    self.df_odds = pd.DataFrame()
    self.last_refresh = 0
    self.refresh_interval = tools.HOUR
    self.refreshOdds()

  def queryOdds(self):
    """Query JSONOdds source, log query time, save dataframe of results
    """
    with open(self.query_log, 'a+') as f:
      lines = 0
      lines_today = 0
      for line in f:
        query_date = datetime.datetime.strptime(line, "%Y%m%d.%H:%M:%S")
        if query_date.date() == datetime.datetime.utcnow().date():
          lines_today += 1
        lines +=1
      if lines_today >= self.query_per_month / 30:
        print("Max queries exceeded today")
        return
      else:
        #going to query, write date
        f.write(datetime.datetime.utcnow().strftime("%Y%m%d.%H:%M:%S") + "\n")
    
    url = "https://jsonodds.com/api/odds/?oddType=Game"
    header = {"x-api-key": config.JSONODDS_API_KEY} 
    r = requests.get(url, headers=header)
    data = json.loads(r.content)
    
    for match in data:
      for odd in match["Odds"][0]:
        match[odd] = match["Odds"][0][odd]
    df = pd.DataFrame(data)
    df['lastUpdated'] = tools.curTime()
    df['league'] = df.Sport.map(self.league_enum)

    df.to_csv(self.query_df, index=False)
    self.df_odds = df
    return

  def loadOdds(self):
    """Loads odds from csv
    """
    try:
      self.df_odds = pd.read_csv(self.query_df)
    except FileNotFoundError:
      return
  
  def refreshOdds(self):
    """Loads odds, checks if empty or update time exceeds refresh
       interval. If exceed refresh interval queries odds.
    """
    if tools.curTime() - self.last_refresh > self.refresh_interval:
      print("Loading odds")
      self.loadOdds()
      if len(self.df_odds) == 0:
        print("Odds not found, querying odds")
        self.queryOdds()
      else:
        #check if the last query was recent
        if tools.curTime() - self.df_odds.lastUpdated.min() > self.refresh_interval:
          print("Odds stale, querying odds")
          self.queryOdds()
    self.last_refresh = tools.curTime()

  def getOdds(self, league, homeTeam, awayTeam, matchType):
    """Gets the odds for a specific league, homeTeam, awayTeam and type of match
    """
    mask = (self.df_odds.league == league) & (self.df_odds.HomeTeam == homeTeam) & (self.df_odds.AwayTeam == awayTeam)
    sl_odds = self.df_odds.loc[mask]
    if len(sl_odds) != 1:
      return np.nan
    if matchType == "game":
      odds = float(sl_odds.iloc[0]["PointSpreadHome"])
      lineHome = float(sl_odds.iloc[0]["PointSpreadHomeLine"])
      lineAway = float(sl_odds.iloc[0]["PointSpreadAwayLine"])
      if np.abs(lineHome) < 80 or np.abs(lineHome) > 120:
        return np.nan
      elif np.abs(lineAway) < 80 or np.abs(lineAway) > 120:
        return np.nan
      else:
        return odds
    elif matchType == "total":
      odds = float(sl_odds.iloc[0]["TotalNumber"])
      lineOver = float(sl_odds.iloc[0]["OverLine"])
      lineUnder = float(sl_odds.iloc[0]["UnderLine"])
      if lineOver > -80 or lineOver < -120:
        return np.nan
      elif lineUnder > -80 or lineUnder < -120:
        return np.nan
      else:
        return odds 





