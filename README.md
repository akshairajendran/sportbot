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

To deploy, instantiate an Engine object with your desired log name: `engine = Engine('quoter')`

### Parameterization



## Built With

* [Python](http://www.python.org)

## Contributing

Please read [CONTRIBUTING.md]() for details on our code of conduct, and the process for submitting pull requests to us.

## Authors

* **Akshai Rajendran** - *Initial work* - [PurpleBooth](https://github.com/akshairajendran)

See also the list of [contributors](https://github.com/akshairajendran/sportbot/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments
