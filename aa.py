#!/usr/bin/env python3
# CryptoCurrency Asset Allocator

import operator
import os
import requests
import sys
import yaml
from tabulate import tabulate
import locale
locale.setlocale(locale.LC_ALL, '')

MIN_WEIGHT = .005  # Minimum market weight to show, unless in portfolio
DATA = requests.get('https://api.coinmarketcap.com/v1/ticker/').json()


def get_price_usd(coin):
    for crypto in DATA:
        if coin == crypto['symbol']:
            return float(crypto['price_usd'])

    # Coin is unlisted
    return 0


def get_crypto_cap_by_percent():
    crypto_by_cap = {}
    crypto_by_usd = {}
    total_cap = 0
    for crypto in DATA:
        if crypto.get('market_cap_usd'):
            total_cap += float(crypto['market_cap_usd'])
            crypto_by_cap[crypto['symbol']] = crypto['market_cap_usd']
            crypto_by_usd[crypto['symbol']] = crypto['price_usd']

    crypto_cap_by_percent = {}
    for symbol, market_cap_usd in crypto_by_cap.items():
        cap_percent = float(market_cap_usd)/float(total_cap)
        crypto_cap_by_percent[symbol] = cap_percent

    return crypto_cap_by_percent


class coin(object):

    def __init__(self, symbol, amount_owned=0):
        self.symbol = symbol
        self.amount_owned = float(amount_owned)
        self.price_usd = get_price_usd(self.symbol)
        self.value_usd = self.amount_owned*self.price_usd


class portfolio(object):
    def __init__(self, assets):
        self.coins = {}
        for symbol, amount in assets.items():
            self.coins[symbol] = coin(symbol, amount)
        self.value = self._get_portfolio_value()
        self.crypto_cap_by_percent = get_crypto_cap_by_percent()
        self.my_cap_by_percent = self._get_my_cap_by_percent()

    def _get_portfolio_value(self):
        value = 0
        for symbol, coin in self.coins.items():
            value += coin.value_usd
        return value

    def _get_my_cap_by_percent(self):
        crypto_by_percent = {}
        for symbol, coin in self.coins.items():
            crypto_by_percent[symbol] = coin.value_usd/self.value
        return crypto_by_percent

    def __repr__(self):
        buf = "\nCurrencies and their relative market weight\n"
        buf += "===========================================\n"
        index = 0
        sorted_crypto_by_percent = sorted(self.crypto_cap_by_percent.items(),
                                          key=operator.itemgetter(1),
                                          reverse=True)

        data = []
        for symbol, market_weight in sorted_crypto_by_percent:
            index += 1
            change_percent = market_weight-self.my_cap_by_percent.get(
                symbol, 0)
            change_usd = change_percent*self.value
            position = 0
            if self.coins.get(symbol):
                position = self.coins[symbol].value_usd
            if (market_weight < MIN_WEIGHT and
                    self.my_cap_by_percent.get(symbol, 0) == 0):
                continue

            spot = get_price_usd(symbol)
            data.append([
                index,
                symbol,
                locale.currency(spot, grouping=True),
                "{:>5.2f}%".format(market_weight*100),
                "{:>5.2f}%".format(self.my_cap_by_percent.get(symbol, 0)*100),
                locale.currency(position, grouping=True),
                locale.currency(change_usd, grouping=True)
                ])

        return tabulate(sorted(data),
                        headers=('Coin', 'Spot', 'Market', 'Port',
                                 'Position', 'Rebalance'), tablefmt="presto")


def usage():
    return "Usage: {} <portfolio.yaml>".format(sys.argv[0])


if __name__ == "__main__":
    if len(sys.argv) < 2 or not os.path.isfile(sys.argv[1]):
        sys.exit(usage())

    with open(sys.argv[1]) as f:
        holdings = yaml.load(f)['portfolio']

    my_port = portfolio(holdings)

    print(my_port)
    print("Total: ${:,.2f}".format(my_port.value))
