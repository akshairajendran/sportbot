import time
import datetime
import websocket
import json
import _thread as thread
from slacker import Slacker
import queue
import logging
import gzip
import config
import tools
from match import Match
from spc import SportCrypt
import order
from logging.handlers import RotatingFileHandler

class Gateway:
  def __init__(self, logName):
    self.matches = {}
    self.matchIdtoName = {}
    self.marketOrders = order.Orders()
    self.pendingOrders = order.Orders()
    self.internalOrders = order.Orders()
    self.books = {}

    self.outbound_messages = {} #log type of message we have sent so we know how to interpret response
    self.response = {}

    self.status = False
    self.shutdown = False
    #self.slack = Slacker(config.SLACK_KEY)
    self.checkPosition = True
    self.report_trade = False
    self.timeout = 5
    self.q = queue.Queue()
    self.messageNumber = 2000
    self.subID = 1235 #subscription id
    self.account_balance = 0
    self.version = "sportbot-0.0.1"
    self.address = config.addressSelf.replace('0x', '')
    self.contractAddr = config.addressSPC.replace('0x', '')
    self.spc = SportCrypt()
    
    ### define parameters for logging ###
    self.logName = logName
    self.md_log = False
    self.trade_log = False

    ### instantiate logger ###
    self.gatewayLogger = logging.getLogger("SPC." + self.logName + "Gateway")
    logFile = '../logs/SPC.' + self.logName + "_" + datetime.datetime.utcnow().strftime("%Y%m%d.%H%M%S") + '.gateway.log'
    hdlr = RotatingFileHandler(logFile, mode='a', maxBytes=500*1024*1024, backupCount=1, encoding=None, delay=0)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    self.gatewayLogger.addHandler(hdlr) 
    self.gatewayLogger.setLevel(logging.DEBUG)

    #self.getInstruments()
    self.tx = []

  def mdLogInit(self):
    self.md_log = True
    ### instantiate MD logger ###
    self.mdLogger = logging.getLogger("SPC." + self.logName + "MarketData")
    logFile = '../mktdata/SPC.' + self.logName + "_" + datetime.datetime.utcnow().strftime("%Y%m%d.%H%M%S") + '.mktdata.gz'
    self.mdLogger.humanLogFile = logFile.replace(".gz", ".csv")
    z_file = gzip.open(logFile, mode='wt', encoding='utf-8')
    hdlr = logging.StreamHandler(z_file)
    #hdlr = logging.FileHandler(logFile, mode='wt', encoding='bz2')
    formatter = logging.Formatter('%(asctime)s %(levelname)s | %(message)s')
    hdlr.setFormatter(formatter)
    self.mdLogger.addHandler(hdlr) 
    self.mdLogger.setLevel(logging.DEBUG)

  def tradeLogInit(self):
    self.trade_log = True
    ### instantiate trade logger ###
    self.tradeLogger = logging.getLogger("SPC." + self.logName + "Trades")
    logFile = '../trades/SPC.' + self.logName + "_" + datetime.datetime.utcnow().strftime("%Y%m%d.%H%M%S") + '.trades.log'
    hdlr = logging.FileHandler(logFile, mode='wt')
    formatter = logging.Formatter('%(asctime)s %(levelname)s | %(message)s')
    hdlr.setFormatter(formatter)
    self.tradeLogger.addHandler(hdlr) 
    self.tradeLogger.setLevel(logging.DEBUG)

  def post_message(self, channel, message):
    try:
      self.slack.chat.post_message(channel, message)
    except Exception as e:
      print("Cannot post: ", channel, message)

  def addMatch(self, match):
    """Takes match message and adds to appropriate maps with details
    """
    m = Match(match)
    self.matches[m.matchName] = m
    self.matchIdtoName[m.matchId] = m.matchName
    return

  def addOrder(self, _order):
    """Takes order message, parses and adds to orders
    """
    orderDict = order.orderParse(_order)
    try:
      self.marketOrders.addOrder(orderDict)
    except Exception as e:
      self.gatewayLogger.error(e)

  def addTx(self, tx):
    """Takes tx-new message and calls appropriate function
    """
    if tx['type'] == 'trade':
      self.addTrade(tx)
    return

  def addTrade(self, tx):
    """Takes trade tx and adds to match position
    """
    if tx['makerAccount'].replace('0x', '') == self.address:
      direction = 'short' if tx['orderDirection'] == '0' else 'long'
    elif tx['takerAccount'].replace('0x', '') == self.address:
      direction = 'long' if tx['orderDirection'] == '0' else 'short'
    else:
      return

    quantity = int(tx['{0}Amount'.format(direction)])
    matchId = tx['matchId'].replace('0x', '')
    if matchId in self.matchIdtoName:
      matchName = self.matchIdtoName[matchId]
    else:
      #match not found
      return
    match = self.matches[matchName]
    if direction == 'short':
      match.shortPosition += quantity
    elif direction == 'long':
      match.longPosition += quantity
    return


  def checkMatches(self):
    """Takes a list of matches and returns match status response
    """
    matches = [self.matches[m].matchId for m in self.matches if self.matches[m].details["expiry"] > tools.curTime()]
    ret = []
    for i in range(0, len(matches), 16):
      out = self.spc.checkMatchBatch(matches[i:i + 16])
      if len(ret) == 0:
        ret = out
      else:
        ret[0] += out[0]
        ret[1] += out[1]
        ret[2] += out[2]
    # for i in range(len(matches)):
    #   matchId = matches[i]
    #   matchName = self.matchIdtoName[matchId]
    #   position = ret[0][i]
    #   self.matches[matchName].position = position
    return ret

  def buildBooks(self):
    """Validates all orders and builds books for all matches
       Must be run to refresh order books
    """
    #expire old orders
    self.marketOrders.expireOrders()

    #flush books
    self.books = {}
    
    #ordered list of internal_ids and corresponding orderDicts
    internal_ids = [internal_id for internal_id in self.marketOrders.orders.keys()]
    orderDicts = [self.marketOrders.orders[internal_id] for internal_id in internal_ids]

    validateLen = int(48 / 3)

    idxRange = range(0, len(orderDicts), validateLen)
    idxLen = len(idxRange)

    toBatch = []
    for i in range(idxLen):
      if i + 1 < idxLen:
        toBatch.append(orderDicts[idxRange[i]:idxRange[i + 1]])

      else:
        toBatch.append(orderDicts[idxRange[i]:])

    toValidate = [self.marketOrders.orderBatch(batch) for batch in toBatch]

    resultStatus = []
    resultAmount = []
    for v in toValidate:
      result = self.spc.checkOrderBatch(v)
      resultStatus += result[0]
      resultAmount += result[1]
    resultStatus = resultStatus[:len(orderDicts)]
    resultAmount = resultAmount[:len(orderDicts)]

    for i in range(len(orderDicts)):
      internal_id = internal_ids[i]
      orderDict = orderDicts[i]
      matchId = orderDict["details"]["matchId"]
      matchName = self.matchIdtoName[matchId]
      if resultStatus[i] != 0:
        self.gatewayLogger.info("Got invalid order status {0} for {1}".format(matchId, orderDict))
        continue
      if resultAmount[i] == 0 or resultAmount[i] == 1:
        continue
      if matchName not in self.books.keys():
        self.books[matchName] = {
                                 "bids":[], #insert tuples of type (price, quantity, internal_id)
                                 "asks":[]
                                }
      quantity = resultAmount[i]
      side = "buy" if orderDict["details"]["direction"] == 1 else "sell"
      price = orderDict["details"]["price"]# if side == "buy" else (1 - orderDict["details"]["price"])
      if side == "buy":
        self.books[matchName]["bids"].append((price, quantity, internal_id))
        self.books[matchName]["bids"] = sorted(self.books[matchName]["bids"], key=lambda x:x[0], reverse=True)
      elif side == "sell":
        self.books[matchName]["asks"].append((price, quantity, internal_id))
        self.books[matchName]["asks"] = sorted(self.books[matchName]["asks"], key=lambda x:x[0])
    return

  def submitOrder(self, matchName, side, price, quantity, expiry):
    contractAddr = self.contractAddr
    matchId = self.matches[matchName].matchId
    direction = 0 if side == "sell" else 1
    fromAddr = self.address
    toHash, orderHash = self.marketOrders.pack(contractAddr, matchId, quantity, expiry, price, direction, fromAddr)

    sig = self.spc.w3.eth.account.signHash(orderHash, private_key=config.keySelf)
    orderMsg = '{0}{1}'.format(toHash, self.spc.w3.toHex(sig['signature']).replace('0x', ''))
    self.orderSubmit = (toHash, orderHash, orderMsg, sig)
    
    self.messageNumber += 1
    toQueue = [{"op":"add-order", "id":self.messageNumber}, {"order":orderMsg}]
    self.q.put(toQueue)
    self.gatewayLogger.info("Submiting order {0}".format(orderMsg))
    self.outbound_messages[self.messageNumber] = "order"
    #add to pending orders
    rawOrderDict = order.orderParse(orderMsg)
    self.pendingOrders.addOrder(rawOrderDict, orderId=self.messageNumber)

    return self.messageNumber

  def orderResponse(self, header, message):
    """Handles response to an order submission
    """
    messageId = header["id"]
    self.gatewayLogger.info("Handling response for order {0}".format(messageId))
    if message["status"] == "ok":
      #success, remove from pendingOrders and add to internalOrders
      orderDict = self.pendingOrders.orders.pop(messageId, None)
      assert orderDict is not None
      rawOrderDict = self.internalOrders.toRaw(orderDict)
      self.internalOrders.addOrder(rawOrderDict, orderId=messageId)
      self.gatewayLogger.info("Got successful response for order {0}, moving from pending to internal".format(messageId))
    else:
      #failure, remove from pendingOrders
      orderDict = self.pendingOrders.orders.pop(messageId, None)
      assert orderDict is not None
      self.gatewayLogger.info("Got unsuccessful response for order {0}, removing from pending".format(messageId))

  def websocket(self):
    def on_message(ws, message):
      #define message handling functions
      def _skip(header, message):
        #unwanted message, skipping
        return

      def _log(header, message):
        #logs message
        self.gatewayLogger.info("Got message type {0}: {1}".format(message["op"], message))

      def _match(header, message):
        #handle new match
        self.addMatch(message['match'])

      def _order(header, message):
        #handle order
        self.addOrder(message['order'])
        
      
      def _transaction(header, message):
        self.gatewayLogger.info("Got transaction: {0}".format(message))
        self.addTx(message['tx'])
        return

      def _response(header, message):
        #handle response message
        messageId = header["id"]
        #lookup message type that we sent
        messageType = self.outbound_messages[messageId]
        self.gatewayLogger.info("Got {0} type response message: {1}".format(messageType, message))
        response_handler[messageType](header, message)
        return

      handler = {
      "bulletin-new":_skip,
      "bulletin-latest":_skip,
      "chatmsg-new":_skip,
      "chatmsg-latest":_skip,
      "match-new":_match,
      "match-latest":_log,
      "order-new":_order,
      "order-latest":_skip,
      "tx-new":_transaction,
      "tx-latest":_log,
      "txstream-new":_skip,
      "txstream-latest":_skip,
      "vol-new":_skip,
      "vol-latest":_skip,
      "response":_response,
      }

      response_handler = {
      "order":self.orderResponse
      }

      def _handle(header, message):
        op = message["op"]
        if op not in handler:
          self.gatewayLogger.info("Got unknown message type: {0}".format(op))
          return
        else:
          handler[op](header, message)

      self.last_heartbeat = datetime.datetime.utcnow()
      if self.shutdown:
        print("I've been told to shutdown")
        ws.keep_running = False
        ws.close()

      rawmessage_list = message.splitlines()
      message_list = [json.loads(message) for message in rawmessage_list]
      header = message_list[0]
      body = message_list[1]

      if header["id"] == 1233 or header["id"] == 1234:
        #self.gatewayLogger.info("Got heartbeat")
        return
      elif header["id"] == self.subID:
        self.gatewayLogger.info("Got subscription response")
        for message in body:
          _handle(header, message)
      elif "op" not in body:
        body["op"]="response"
        _handle(header, body)
      else:
        self.gatewayLogger.info("Got unrecognized message: {0}, {1}".format(header, body))
     


    def on_error(ws, error):
      self.gatewayLogger.error(error)
      print(error)

    def on_close(ws):
      print("### closed ###")
      self.status = False
      self.checkPosition = True

    def on_open(ws):
        self.last_heartbeat = datetime.datetime.utcnow()

        def heartbeat(*args):
          set_heartbeat = {
          "id":1233,
          "op": "ping"
          }
          
          try:
            ws.send(json.dumps(set_heartbeat) + '\n{}')
          except:
            #we were unable to set heartbeat, kill everything
            print("Setting heartbeat failed")
            self.status = False
            self.shutdown = True
            ws.keep_running = False
            ws.close()
            return

          while True:
            if (datetime.datetime.utcnow() - self.last_heartbeat).total_seconds() > self.timeout:
              print("Missed a heartbeat")
              #check last received heartbeat
              self.status = False
              self.shutdown = True
            if self.shutdown:
              if ws.keep_running:
                ws.keep_running = False
                ws.close()
              break
            message = {
            "id": 1234,
            "op": "ping"
            }
            ws.send(json.dumps(message) + '\n{}')
            #self.gatewayLogger.info("Sent heartbeat")
            time.sleep(2)
          return

        def sender(*args):
          while True:
            if self.shutdown:
              #clear the q
              with self.q.mutex:
                self.q.queue.clear()
              break
            if self.status:
              #only get data and send if we're connected
              try:
                data = self.q.get_nowait()
                ws.send(json.dumps(data[0]) + '\n' + json.dumps(data[1]))
              except queue.Empty:
                pass
            time.sleep(.001)
          return

        header = {
                  "id": self.subID, 
                  "op": "subs",  
                 }
        data = {
                "bulletin":0,
                "match":0,
                "chatmsg":0,
                "all-orders":"true",
                "txstream":0,
                "vol":0,
                "tx-address":self.address,
                "client":self.version
               }

        ws.send(json.dumps(header) + "\n" + json.dumps(data))
        print("Starting websocket...")
        thread.start_new_thread(heartbeat, ())
        print("Starting heartbeat...")
        thread.start_new_thread(sender, ())
        print("Starting sender...")

        self.status = True

    #websocket.enableTrace(False)
    ws = websocket.WebSocketApp("wss://sportcrypt.com/ws-mainnet/",
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()
