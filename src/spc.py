from web3 import Web3, HTTPProvider
import tools
import config
import json

class SportCrypt():
  def __init__(self, addressContract=config.addressSPC, addressSelf=config.addressSelf, abi='lib/SportCrypt.json'):
    """Initializes class for SportCrypt smart contract
    """
    #self.provider = Web3.IPCProvider(config.IPC_ADDR)
    self.provider = HTTPProvider('https://mainnet.infura.io/{0}'.format(config.INFURA_API_KEY))
    self.w3 = Web3(self.provider)
    self.addressContract = addressContract
    self.addressSelf = addressSelf
    self.checksumContract = self.w3.toChecksumAddress(self.addressContract)
    self.checksumSelf = self.w3.toChecksumAddress(self.addressSelf)
    with open(abi, 'r') as f:
      abiParse = json.load(f)
    self.contract = self.w3.eth.contract(self.checksumContract, abi=abiParse['contracts']['SportCrypt.sol:SportCrypt']['abi'])

  ###Free function calls###
  def getBalance(self):
    """Returns balance in addressContract for addressSelf in Wei
    """
    return self.contract.functions.getBalance(self.checksumSelf).call()

  def checkOrderBatch(self, orderBatch):
    """Returns result of checkOrderBatch, must pass a list of lengh 48
    """
    assert len(orderBatch) == 48
    return self.contract.functions.checkOrderBatch(orderBatch).call()

  def checkMatchBatch(self, matchBatch):
    """Returns result of checkMatchBatch, extends list to length 16 with empty strings
    """
    assert len(matchBatch) <= 16
    len_input = len(matchBatch)
    matchBatch = [tools.parseInt(m) for m in matchBatch]
    for i in range(len_input, 16):
      matchBatch.append(0)
    ret = self.contract.functions.checkMatchBatch(self.checksumSelf, matchBatch).call()
    ret = [r[:len_input] for r in ret]
    return ret



