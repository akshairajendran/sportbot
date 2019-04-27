# sportbot

sportbot is an automated market making bot for [Sportcrypt](https://sportcrypt.com) Ethereum Sports Betting Smart Contracts.

*sportbot prices and maintains two-sided markets in all Sportcrypt contracts using a live odds feed from [JSONOdds](https://jsonodds.com)
*sportbot uses historical game data from [SportsDatabase.com](https://sportsdatabase.com) to price over/under and point spread bets

### Prerequisites

sportbot runs on Python and requires the packages specified in requirements.txt. 
It interacts with Sportcypt's smart contracts via websockets and web3.py over HTTP using [INFURA](https://infura.io) as the provider so no local Ethereum node is necessary. However, an option is provided for implementation using a local node.

## Installing

1. Make sure that your machine has Python 3.6 or greater installed
2. Clone the repository
3. cd to the src directory and run `pip -r requirements.txt` to install all required python packages

###Configuration

4. Create a config.py file in the src directory with the following variables:


## Deployment

Add additional notes about how to deploy this on a live system

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
