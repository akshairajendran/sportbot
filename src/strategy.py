import tools
import numpy as np

class Strategy():
  def __init__(self, match, edge=10, size=1000000000000000, duration=tools.MINUTE*2, quoter=False, hitter=False):
    self.match = match #match object
    self.edge = edge
    self.size = size
    self.duration = duration
    self.quoter = quoter
    self.hitter = hitter
    self.bid = {"price":0, "orderId":0, "enabled":(quoter or hitter), "status":"dead", "expiry":0, "quantity":0}
    self.ask = {"price":100, "orderId":0, "enabled":(quoter or hitter), "status":"dead", "expiry":0, "quantity":0}
    self.backup = 1

  def getQuotes(self, theo, book):
    """Returns quotes, if quoter disabled returns quotes at max width
    """
    self.expireOrders()
    best_bid = book["bids"][0][0]
    best_ask = book["asks"][0][0]
    
    if self.bid["enabled"] and self.quoter and self.bid["status"] == "dead" and not np.isnan(theo):
      bid_price = int(theo - self.edge)
      bid_size = self.size
      bid_expiry = tools.curTime() + self.duration

      if bid_price > best_ask:
        bid_price = best_ask - self.backup
    else:
      bid_price = 0
      bid_size = 0
      bid_expiry = 0

    if self.ask["enabled"] and self.quoter and self.ask["status"] == "dead" and not np.isnan(theo):
      ask_price = int(round(theo + self.edge + 0.5))
      ask_size = self.size
      ask_expiry = tools.curTime() + self.duration

      if ask_price < best_bid:
        ask_price = best_bid + self.backup
    else:
      ask_price = 100
      ask_size = 0
      ask_expiry = 0

    return [(bid_price, int(bid_size), int(bid_expiry)), (ask_price, int(ask_size), int(ask_expiry))]

  def getHits(self, theo, book):
    """Returns hits, if hitter disabled returns hits at max width
       Takes a book of bid ask and if applicable returns an order to trade
    """ 
    return

  def updateOrder(self, side, sideId, price, status, expiry, quantity):
    """Takes side as self.bid or self.ask and updates with id, price, status, expiry, quantity
    """
    side["orderId"] = sideId
    side["price"] = price
    side["status"] = status
    side["expiry"] = expiry
    side["quantity"] = quantity
    return

  def expireOrders(self):
    """Expires outstanding bid and ask if past expiration time
    """
    now = tools.curTime()
    if self.bid["expiry"] < now:
      self.bid["price"] = 0
      self.bid["orderId"] = 0
      self.bid["status"] = "dead"
      self.bid["expiry"] = 0
      self.bid["quantity"] = 0
    if self.ask["expiry"] < now:
      self.ask["price"] = 100
      self.ask["orderId"] = 0
      self.ask["status"] = "dead"
      self.ask["expiry"] = 0
      self.ask["quantity"] = 0

