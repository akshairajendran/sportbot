import tools
import pandas as pd
import numpy as np
import scipy.stats as stats
from jsonodds import JSONOdds

class Pricing():
  def __init__(self):
    self.database = {
    "nba": "../data/nba.20150101.20190107.csv",
    "ncaab": "../data/ncaabb.20130101.20190114.csv",
    "ncaaf": "../data/ncaafb.20130101.20190114.csv",
    "nfl": "../data/nfl.20130101.20190114.csv",
    "nhl": "../data/nhl.20130101.20190114.csv",
    "ahl": None,
    "soccer": None,
    "khl": None,
    }

    self.pricingByLeague = {}

    self.maxTheo = 70
    self.minTheo = 30
    self.EPS = .5

    self.loadPricing()
    self.odds = JSONOdds()

  def loadPricing(self):
    """Loads pricing from database into self.data
    """
    for league in self.database:
      filepath = self.database[league]
      if filepath:
        df_data = pd.read_csv(filepath).drop("Unnamed: 0", axis=1)
      else:
        self.pricingByLeague[league] = (np.nan, np.nan)
        continue

      s_total = pd.to_numeric(df_data['ou margin'], errors='coerce')
      if np.abs(s_total.mean()) < self.EPS:
        total_std = s_total.std()
      else:
        total_std = np.nan
        print("Unable to load pricing for {0} total, abs mean of {1} > {2}".format(league, np.abs(s_total.mean()), self.EPS))
      
      s_game = pd.to_numeric(df_data['margin'], errors='coerce') + pd.to_numeric(df_data['line'], errors='coerce')
      if np.abs(s_game.mean()) < self.EPS:  
        game_std = s_game.std()  
      else:
        game_std = np.nan
        print("Unable to load pricing for {0} game, abs mean of {1} > {2}".format(league, np.abs(s_game.mean()), self.EPS))

      self.pricingByLeague[league] = (total_std, game_std)

  def getPricing(self, league):
    """Loads data for the specified league, if unable to find returns nan tuple
    """
    if league in self.pricingByLeague:
      return self.pricingByLeague[league]
    else:
      return (np.nan, np.nan)

  def getTheo(self, match):
    """Returns pricing for match
    """
    self.odds.refreshOdds()
    vegas = self.odds.getOdds(match.details["league"], match.details["team2"], match.details["team1"], match.details["type"])
    total_std, game_std = self.getPricing(match.details['league'])
    strike = match.details['strike']

    if match.details['type'] == 'total':
      std = total_std
    elif match.details['type'] == 'game':
      std = game_std
    theo = stats.norm(0, std).cdf(vegas - strike) * 100

    #safety check theos
    if theo > self.maxTheo or theo < self.minTheo:
      print("Violated theo limit with: {0}, {1}".format(theo, match.matchName))
      return np.nan

    return theo