import tools
import config
import numpy as np

class Match():
  def __init__(self, _match):
    """Takes match message as _match from exchange
    """
    self.matchId = _match["id"]
    self.linkId = _match["linkid"]
    
    strike_map = {
    "game":"spread",
    "total":"total",
    }

    self.details = {}
    self.details['expiry'] = int(_match["details"]["event"]["kickoff"]) * 10**9
    self.details['league'] = _match["details"]["type"].split("/")[1]
    self.details['type'] = _match["details"]["type"].split("/")[2]
    self.details['str_strike'] = _match["details"]["event"][strike_map[self.details["type"]]]
    self.details["strike"] = float(self.details["str_strike"])
    self.details['team1'] = _match["details"]["event"]["team1"]
    self.details['team2'] = _match["details"]["event"]["team2"]
    self.details["nonce"] = _match["details"]["nonce"]
    self.details["recoveryWeeks"] = int(_match["details"]["recoveryWeeks"])
    self.details["cancelPrice"] = int(_match["details"]["cancelPrice"])
    self.details["contractAddr"] = _match["details"]["contractAddr"]

    self.details["settlePrice"] = np.nan
    if "fin" in _match:
      if "finalPrice" in _match["fin"]:
        self.details["settlePrice"] = _match["fin"]["finalPrice"]
    

    self.matchName = "SPC.{0}@{1}_{2}_{3}".format(self.details["team1"], self.details["team2"], self.details["type"], self.details["str_strike"])




