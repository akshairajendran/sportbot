# sportbot

sportbot is an automated market making bot for [Sportcrypt](https://sportcrypt.com) Ethereum Sports Betting Smart Contracts.

* sportbot prices and maintains two-sided markets in all Sportcrypt contracts using a live odds feed from [JSONOdds](https://jsonodds.com)
* sportbot uses historical game data from [SportsDatabase.com](https://sportsdatabase.com) to price over/under and point spread bets

### Prerequisites

sportbot runs on Python and requires the packages specified in requirements.txt. 
It interacts with Sportcypt's smart contracts via websockets and web3.py over HTTP using [INFURA](https://infura.io) as the provider so no local Ethereum node is necessary. However, an option is provided for implementation using a local node.

## Installing

1. Make sure that your machine has Python 3.6 or greater installed
2. Clone the repository
3. cd to the src directory and run `pip -r requirements.txt` to install all required python packages

### Configuration

4. Create a config.py file in the src directory with the following variables:
   - addressSelf which contains the address of your Ethereum wallet or the contract from which you will be sending/receiving funds
   - keySelf which contains the private key to addressSelf
   - addressSPC which contains the address to the Sportcrypt smart contract and can be found on their site
   - INFURA_API_KEY which contains the API key to your Mainnet Infura account if using HTTP provider
   - IPC_ADDR which contains the filepath to your local IPC endpoint if using a local node as the provider
   - JSONODDS_API_KEY which contains the API key to your JSONOdds account
5. **DO NOT** share your config.py file with anyone as it contains sensitive information regarding your smart contract and other API access

## Usage

To deploy, instantiate an Engine object with your desired log name: `engine = Engine('quoter')`. Quotes are automatically added for all leagues by default for which pricing exists. To begin quoting run `engine.run()`.

### Parameterization

The following parameters pertain to top level risk:
- engine.account_bal_tolerance specifies in Wei the most your account balance may decrease from its maximum value before killing the engine
- engine.maxNotionalOutstanding specifies in Wei the max notional risk you may have outstanding, additional quote will not be submitted if this limit is reached
- engine.max_rejects specifies the maximum number of automatic restarts the engine may make on non-critical errors
- engine.leagues specifies which leagues to quote in and follows the naming convention specified by Sportcrypt
- engine.matchTypes specifies the match or bet types in which to place quotes and follows the naming convention specified by Sportcrypt
- engine.strategyParams specifies the default parameters by which new strategies are instantied
  - strategyParams.edge specifies the edge in contract price (0-100) at which to place quotes
  - strategyParams.size specifies the quantity in Wei at which to place quotes
  - strategyParams.duration specifies the duration in nanoseconds at which to place quotes, after which they will be expired by the exchange
  - strategyParams.quoter is a boolean specifying whether the strategy is submitting quotes or not
  - strategyParams.hitter is a boolean specifying whether the strategy is submitting hits or not (hitter to be implemented)

### Pricing

Pricing combines live odds and historical game results to compute prices for over/under bets at any point line and point spread bets at any spread. Live odds are taken from JSONOdds and assumed to be fairvalue, i.e. for the Golden State Warriors, Milwaukee Bucks game JSONOdds is predicting a total score of 225 points and a margin of 10 points for the Warriors then a contract with an over/under of 225 and a contract with a point spread of +10 for the Bucks are both priced at 50. However, we are not guaranteed to be placing quotes on these contracts--if so, pricing would be trivial. If on the Warriors-Bucks game, Sportcrypt is listing an over/under contract at 230 and a point spread contract at +7 we must determine the fair value of these contracts--which we know is not equal to 50--in order to place quotes. sportbot prices these contracts by computing the historical distribution of NBA scores and assuming the score of this game will be distributed identically with a mean of 230. For exact details on implementation, see [pricing.py](https://github.com/akshairajendran/sportbot/blob/master/src/pricing.py)

## Built With

* [Python](http://www.python.org)

## Contributing

Please read [CONTRIBUTING.md](https://github.com/akshairajendran/sportbot/blob/master/CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## Authors

* **Akshai Rajendran** - *Initial work* - [sportbot](https://github.com/akshairajendran/sportbot)

See also the list of [contributors](https://github.com/akshairajendran/sportbot/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](https://github.com/akshairajendran/sportbot/blob/master/LICENSE.md) file for details

## Acknowledgments

Thanks to the Sportcrypt team for helping me with their API and working with me to debug any issues I had.
