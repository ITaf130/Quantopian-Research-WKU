import talib
import numpy as np
import pandas as pd


def initialize(context):
    context.stock = sid(700)
    context.date = None
    set_benchmark(context.stock)
    context.prevmacd = 0
    context.macdtracker= 0

def handle_data(context, data):
    todays_date = get_datetime().date()

    # makes sure you only trade once a day
    if todays_date == context.date:
        return

    context.date = todays_date
    context.macdtracker = context.prevmacd
    prices = data.history(context.stock, 'price', 50, '1d')
    macdline = MACD(prices, fastperiod=12, slowperiod=26, signalperiod=9)
    macdsignal = signal(prices, fastperiod= 12, slowperiod = 26, signalperiod=9)
    macdhisto= macdline- macdsignal

    stock = context.stock
    position = context.portfolio.positions[stock].amount
    # If macd crosses back over, liquidate
    if macdhisto > 0 and position == 0:
        order_target_percent(stock, 0.99)
    # When macd crosses over to positive, full position
    elif macdhisto < 0 and position > 0:
        order_target_percent(stock, 0)
        

    context.prevmacd = macdhisto

    record(currentmacd=macdhisto)


def MACD(prices, fastperiod=12, slowperiod=26, signalperiod=9):
    macd, signal, hist = talib.MACD(prices,
                                    fastperiod=fastperiod,
                                    slowperiod=slowperiod,
                                    signalperiod=signalperiod)
    return macd[-1]
def signal(prices, fastperiod=12, slowperiod=26, signalperiod=9):
    macd, signal, hist = talib.MACD(prices,
                                    fastperiod=fastperiod,
                                    slowperiod=slowperiod,
                                    signalperiod=signalperiod)
    return signal[-1]