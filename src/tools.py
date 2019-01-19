from web3 import Web3
import datetime
import pytz

SECOND = 10 ** 9
MINUTE = SECOND * 60
HOUR = MINUTE * 60
DAY = HOUR * 24

def curTime():
  """Returns current time in nanoseconds since epoch (UTC)
  """
  return int(pytz.UTC.localize(datetime.datetime.utcnow()).timestamp()*10**9)

def toEpoch(timestamp):
  """Takes a datetime object and returns nanoseconds since epoch (UTC)
  """
  return int(pytz.UTC.localize(timestamp).timestamp()*10**9)

def parseInt(hex):
  """Takes hex, appends 0x and returns integer
  """
  return int("0x{0}".format(hex), 16)
