import tools
import config
from web3 import Web3 as w3
import sha3
import codecs

def orderParse(orderString):
  """Parse packed value of order message
  """
  assert len(orderString) == 362
  contractAddr = orderString[0:40]
  matchId = orderString[40:104]
  amount = orderString[104:168]
  expiry = orderString[168:178]
  nonce = orderString[178:188]
  price = orderString[188:190]
  direction = orderString[190:192]
  fromAddress = orderString[192:232]

  detailsDict = {
  "contractAddr":contractAddr,
  "matchId":matchId,
  "amount":amount,
  "expiry":expiry,
  "nonce":nonce,
  "price":price,
  "direction":direction,
  "fromAddress":fromAddress
  }
  
  rawOrder = ''.join([detail for detail in detailsDict.values()])
  orderHash = w3.toHex(w3.sha3(text=rawOrder))

  v = orderString[360:362]
  r = orderString[232:296]
  s = orderString[296:360]

  sigDict = {
  'v':v,
  'r':r,
  's':s
  }

  orderDict = {
  'details':detailsDict,
  'hash':orderHash,
  'sig':sigDict
  }

  return orderDict

class Orders():
  def __init__(self):
    """No inputs needed
    """

    self.orders = {}
    self.internal_id = 0

  def addOrder(self, rawOrderDict, orderId=None):
    orderDict = self.fromRaw(rawOrderDict)

    if orderDict["details"]["expiry"] >= tools.curTime():
      self.orders[orderId if orderId else self.internal_id] = orderDict
      self.internal_id += 0 if orderId else 1

  def expireOrders(self):
    """Removes orders from order map if expired
    """
    to_del = []
    for order in self.orders:
      orderDict = self.orders[order]
      expiry = orderDict["details"]["expiry"]
      if expiry < tools.curTime():
        to_del.append(order)
    for order in to_del:
      self.orders.pop(order, None)

  def fromRaw(self, rawOrderDict):
    """Convers raw orderDict into human readable
    """
    orderDict = {}
    orderDict["details"] = rawOrderDict["details"].copy()
    orderDict["hash"] = rawOrderDict["hash"]
    orderDict["sig"] = rawOrderDict["sig"]

    orderDict["details"]["amount"] = tools.parseInt(orderDict["details"]["amount"])
    orderDict["details"]["expiry"] = tools.parseInt(orderDict["details"]["expiry"])*10**9
    orderDict["details"]["price"] = tools.parseInt(orderDict["details"]["price"])
    orderDict["details"]["direction"] = tools.parseInt(orderDict["details"]["direction"])

    return orderDict

  def toRaw(self, orderDict):
    """Convers human readable orderDict into raw
    """
    rawOrderDict = {}
    rawOrderDict["details"] = orderDict["details"].copy()
    rawOrderDict["hash"] = orderDict["hash"]
    rawOrderDict["sig"] = orderDict["sig"]

    rawOrderDict["details"]["amount"] = hex(rawOrderDict["details"]["amount"]).replace('0x','').zfill(64)
    rawOrderDict["details"]["expiry"] = hex(int(rawOrderDict["details"]["expiry"] / 10**9)).replace('0x','').zfill(10)
    rawOrderDict["details"]["price"] = hex(rawOrderDict["details"]["price"]).replace('0x','').zfill(2)
    rawOrderDict["details"]["direction"] = hex(rawOrderDict["details"]["direction"]).replace('0x','').zfill(2)

    return rawOrderDict

  def orderBatch(self, orderDicts):
    """Takes a list of human readable orderDicts and returns a list of integers containing order details
       This batch is extended to len 48 and can be passed into the smart contract
    """
    batch = []
    for orderDict in orderDicts:
      rawOrderDict = self.toRaw(orderDict)
      int0 = tools.parseInt(rawOrderDict['details']['matchId'])
      int1 = tools.parseInt(rawOrderDict['details']['amount'])
      int2 = tools.parseInt('{0}{1}{2}{3}{4}'.format(rawOrderDict['details']['expiry'],
                                                     rawOrderDict['details']['nonce'],
                                                     rawOrderDict['details']['price'],
                                                     rawOrderDict['details']['direction'],
                                                     rawOrderDict['details']['fromAddress']))
      batch.append(int0)
      batch.append(int1)
      batch.append(int2)

    #extend batch
    batch += [0 for i in range(48 - len(batch))]

    return batch

  def pack(self, contractAddr, matchId, amount, expiry, price, direction, fromAddress):
    """Takes [contractAddr], [matchId] and [fromAddress] and hex and amount, expiry, price, direction
       as integers. Note that expiry is expected to be in nanoseconds (ERM native) and will be converted
       to seconds
    """
    orderDict = {
                 "details":{
                            "matchId":matchId,
                            "amount":amount,
                            "expiry":expiry,
                            "nonce":hex(int(tools.curTime() / 10**9)).replace('0x','').zfill(10),
                            "price":price,
                            "direction":direction,
                            "fromAddress":fromAddress
                           },
                  "hash":'',
                  "sig":{
                         "v":"",
                         "r":"",
                         "s":""
                        }
                }
    rawOrderDict = self.toRaw(orderDict)

    # int0 = tools.parseInt(rawOrderDict['details']['matchId'])
    # int1 = tools.parseInt(rawOrderDict['details']['amount'])
    # int2 = tools.parseInt('{0}{1}{2}{3}{4}'.format(rawOrderDict['details']['expiry'],
    #                                                rawOrderDict['details']['nonce'],
    #                                                rawOrderDict['details']['price'],
    #                                                rawOrderDict['details']['direction'],
    #                                                rawOrderDict['details']['fromAddress']))
    #toHash = "{0}{1}{2}{3}".format(contractAddr, int0, int1, int2)
    toHash = '{0}{1}{2}{3}{4}{5}{6}{7}'.format(contractAddr,
                                               rawOrderDict['details']['matchId'],
                                               rawOrderDict['details']['amount'],
                                               rawOrderDict['details']['expiry'],
                                               rawOrderDict['details']['nonce'],
                                               rawOrderDict['details']['price'],
                                               rawOrderDict['details']['direction'],
                                               rawOrderDict['details']['fromAddress'],
                                              )
    orderHash0 = sha3.keccak_256()
    orderHash0.update(codecs.decode(toHash, 'hex_codec'))
    orderHash1 = sha3.keccak_256()
    orderHash1.update(u"\x19Ethereum Signed Message:\n32".encode('utf-8') + orderHash0.digest())
    orderHash = w3.toHex(orderHash1.digest())

    return toHash, orderHash



