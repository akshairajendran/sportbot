from threading import Thread
import gateway
import time
import tools
import strategy
import pricing
import datetime
import config
import logging
from logging.handlers import RotatingFileHandler

class Engine():
  def __init__(self, logName):
    self.logName = logName
    self.exchange = "SPC"
    #instantiate pricing and gateway modules
    self.gateway = gateway.Gateway(logName=logName)
    self.pricing = pricing.Pricing()
    #create strategies array
    self.strategies = []
    self.maxStrategiesPerMatch = 1
    self.strategiesByMatch = {} #dictionary of lists, lists contain pointers to self.strategies

    #balance related parameters
    self.account_bal_watermark = 0
    self.account_bal_tolerance = (.1)*10**18

    #LIMITS
    self.maxNotionalOutstanding = (.5)*10**18
    self.notionalOutstanding = 0

    ### instantiate logger ###
    self.logger = logging.getLogger(self.exchange + "." + logName)
    logFile = '../logs/' +  self.exchange + '.' + logName + "_" + datetime.datetime.utcnow().strftime("%Y%m%d.%H%M%S") + '.log'
    hdlr = RotatingFileHandler(logFile, mode='a', maxBytes=500*1024*1024, backupCount=5, encoding=None, delay=0)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    self.logger.addHandler(hdlr) 
    self.logger.setLevel(logging.DEBUG)

    #reject related parameters
    self.reject_counter = 0
    self.max_rejects = 2

    #misc parameters
    self.loop_counter = 0

    #STRATEGY
    self.leagues = ["all"]
    self.matchTypes = ["all"]
    self.strategyParams = {
                           "edge":3,
                           "size":(.01)*10**18,
                           "duration":tools.MINUTE*10,
                           "quoter":True,
                           "hitter":False,
                          }

  def loadFromParams(self):
    """Loads all strategies from specified params, not safe if maxStrategiesPerMatch > 1 right now
    """
    assert self.maxStrategiesPerMatch == 1
    for league in self.leagues:
      for matchType in self.matchTypes:
        edge = self.strategyParams["edge"]
        size = self.strategyParams["size"]
        duration = self.strategyParams["duration"]
        quoter = self.strategyParams["quoter"]
        hitter = self.strategyParams["hitter"]

        self.loadStrategies(league=league, matchType=matchType, edge=edge, size=size, duration=duration,
                            quoter=quoter, hitter=hitter)

  def loadStrategies(self, league="all", matchType="all", 
                           edge=3, size=10000000000000000, duration=tools.MINUTE*10,
                           quoter=False, hitter=False):
    """Loads strategies in league specified of type specified
    """
    for m in self.gateway.matches:
      match = self.gateway.matches[m]
      if match.details["expiry"] < tools.curTime():
        continue
      if match.details["league"] != league and league != "all":
        continue
      if match.details["type"] != matchType and matchType != "all":
        continue
      if match.matchName in self.strategiesByMatch:
        if len(self.strategiesByMatch[match.matchName]) >= self.maxStrategiesPerMatch:
          continue
      else:
        self.strategiesByMatch[match.matchName] = []
      #if we've made it this far, we want to add this match
      self.logger.info("Adding strategy for {0} with edge {1}, size {2}, quoter status {3}, hitter status {4}".format(match.matchName, edge, size, quoter, hitter))
      s = strategy.Strategy(match, edge, size, duration, quoter, hitter)
      idx = len(self.strategies)
      self.strategies.append(s)
      self.strategiesByMatch[match.matchName].append(idx)

  def updateOrders(self, strategy):
    """Updates order status of strategy orders
    """
    bidId = strategy.bid["orderId"]
    askId = strategy.ask["orderId"]

    self.gateway.pendingOrders.expireOrders()
    self.gateway.internalOrders.expireOrders()

    if bidId in self.gateway.pendingOrders.orders:
      strategy.bid["status"] = "pending"
    elif bidId in self.gateway.internalOrders.orders:
      strategy.bid["status"] = "live"
    else:
      strategy.bid["status"] = "dead"

    if askId in self.gateway.pendingOrders.orders:
      strategy.ask["status"] = "pending"
    elif askId in self.gateway.internalOrders.orders:
      strategy.ask["status"] = "live"
    else:
      strategy.ask["status"] = "dead"

  def getBook(self, matchName):
    book = {"bids":[(0, 0, 0)], "asks":[(100, 0, 0)]}
    if matchName in self.gateway.books:
      book = self.gateway.books[matchName]
      if len(book["bids"]) == 0:
        book["bids"] = [(0, 0, 0)]
      if len(book["asks"]) == 0:
        book["asks"] = [(100, 0, 0)]
    return book

  def submitOrders(self, strategy):
    """Gets orders from a given strategy and submits if applicable
    """
    if strategy.match.details['expiry'] < tools.curTime():
      return

    theo = self.pricing.getTheo(strategy.match)
    book = self.getBook(strategy.match.matchName)
    self.updateOrders(strategy)
    #get quotes and submit
    quotes = strategy.getQuotes(theo, book)
    #hits = strategy.getHits(theo)
    bid = quotes[0]
    ask = quotes[1]

    if not self.pretrade_riskcheck():
      return
    if bid[0] > 0 and bid[1] > 0 and bid[2] > tools.curTime():
      bidId = self.gateway.submitOrder(strategy.match.matchName, "buy", bid[0], bid[1], bid[2])
      strategy.updateOrder(strategy.bid, sideId=bidId, price=bid[0], status="pending", expiry=bid[2], quantity=bid[1])
      log_string = "Submitting bid: '{0}' Buy '{1}' @ '{2}'".format(strategy.match.matchName, bid[1], bid[0])
      print(log_string)
      self.logger.info(log_string)

    if not self.pretrade_riskcheck():
      return
    if ask[0] > 0 and ask[1] > 0 and ask[2] > tools.curTime():
      askId = self.gateway.submitOrder(strategy.match.matchName, "sell", ask[0], ask[1], ask[2])
      strategy.updateOrder(strategy.ask, sideId=askId, price=ask[0], status="pending", expiry=ask[2], quantity=bid[1])
      log_string = "Submitting ask: '{0}' Sell '{1}' @ '{2}'".format(strategy.match.matchName, ask[1], ask[0])
      print(log_string)
      self.logger.info(log_string)

  def pretrade_riskcheck(self):
    """Defines pretrade risk checks, returns True if safe to proceed, False if now
    """
    if self.compute_notional() >= self.maxNotionalOutstanding:
      return False
    return True 

  def compute_notional(self):
    """Computes notional outstanding and updates self.notionalOutstanding
    """
    self.notionalOutstanding = 0
    for s in self.strategies:
      if s.match.details["expiry"] < tools.curTime():
        continue
      bid_notional = s.bid['quantity']
      ask_notional = s.ask['quantity']
      self.notionalOutstanding += bid_notional + ask_notional
    return self.notionalOutstanding

  def check_balance(self):
    bal = self.gateway.spc.getBalance()
    if bal > self.account_bal_watermark:
      self.account_bal_watermark = bal
      return True
    else:
      if self.account_bal_watermark - bal > self.account_bal_tolerance:
        return False
      else:
        return True

  def shutdown(self):
    #self.gateway.post_message('#error', str(self.exchange) + " " + str(self.logName) + " " + "shutting down...")
    print("Killing...")
    self.logger.warning("Killing...")
    self.gateway.shutdown = True
    time.sleep(4)
    #self.cancel_all(options=options,futures=futures)
    return

  def restart_attempt(self):
    #make sure gateway is shutdown
    self.gateway.shutdown = True

    if self.reject_counter < self.max_rejects:
      self.reject_counter += 1
      #self.gateway.post_message('#error', str(self.exchange) + " " + str(self.logName) + " attempting restart")
      time.sleep(8)
      self.run_init()
      return True
    else:
      #self.gateway.post_message('#error', str(self.exchange) + " " + str(self.logName) + " exceeded max restarts, shutting down.")
      return False

  def run_init(self):
    self.gateway.shutdown = False

    t = Thread(target=self.gateway.websocket)
    t.start()
    time.sleep(5)

    #check balance before beginning loop
    if not self.check_balance():
      print("Balance too low!")
      self.logger.warning("Balance too low!")
      self.shutdown()
      raise BalanceException

  def run(self):
    self.run_init()
    start = time.time()
    last_loop_count = 0

    while True:
      try:
        if time.time() - start > 1:
          print("{0} loops per second".format((self.loop_counter - last_loop_count) / (time.time() - start)))
          start = time.time()
          last_loop_count = self.loop_counter

        self.loop_counter += 1
        self.loop_counter = self.loop_counter % 100000

        time.sleep(.005)

        if not self.gateway.status:
          print("Gateway disconnect...")
          self.logger.warning("Gateway disconnect...")
          self.shutdown()
          if self.restart_attempt():
            continue
          else:
            break

        if self.loop_counter % 1000 == 0:
          self.gateway.buildBooks()
          self.logger.info("Requesting book build from gateway")
          self.loadFromParams()
          self.logger.info("Loading strategies from params")


        # self.updateTheos()
        # self.updateInventory()
        # self.refresh_delta()

        for strategy in self.strategies:
          self.submitOrders(strategy)

      except KeyboardInterrupt:
        print("User interrupt")
        self.logger.warning("User interrupt")
        self.shutdown()
        break
      except BalanceException:
        print("Balance too low!")
        self.logger.warning("Balance too low!")
        self.shutdown()
        #self.gateway.post_message('#error', str(self.exchange) + " " + str(self.logName) + " " + "Balance violated!")
        break
      except Exception as e:
        print("Main run loop error:")
        print(e)
        self.logger.critical(str(e), exc_info=1)
        self.shutdown()
        if self.restart_attempt():
          continue
        else:
          break

    return


class BalanceException(Exception):
  pass
class MissingResponseException(Exception):
  pass
