'''
Pipeline Filters: 
average dollar volume > 10^8 (dv_filter)
stock is in Q1500US (Q1500US)
price > 10 (price_filter)
price > 10-day SMA (positive_movement)
30-day Parkinson Volatility is in bottom 1500 of stocks (pvol_filter)

MACD Histogram Trading

To-DO: 
manage leverage
risk management (determine why algorithm fails)
'''
from quantopian.pipeline import Pipeline
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.filters import Q1500US
from quantopian.pipeline.factors import SimpleMovingAverage
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data import morningstar
from quantopian.pipeline import CustomFactor
import talib
import math
import numpy as np
import pandas as pd
class PriceRange(CustomFactor):  
    # define inputs for the compute method  
    inputs = [USEquityPricing.close]  
    def compute(self, today, assets, out, close):  
        out[:] = close[-1]  
class Parkinson(CustomFactor):
    
    inputs = [USEquityPricing.high, USEquityPricing.low]
    
    def compute(self, today, assets, out, high, low):
        # high and low are data frames with window_lengh rows of data
        # http://www.ivolatility.com/help/3.html
        x = np.log(high/low)
        
        rs = (1.0/(4.0*math.log(2.0)))*x**2
        
        p_vol = np.sqrt(rs.mean(axis=0))

        out[:] = p_vol

class AvgDailyDollarVolumeTraded(CustomFactor):
    inputs = [USEquityPricing.close, USEquityPricing.volume]
    def compute(self, today, assets, out, close_price, volume):
        dollar_volume = close_price * volume
        avg_dollar_volume = np.mean(dollar_volume, axis=0)
        out[:] = avg_dollar_volume

def initialize(context):
    context.max_notional = 100000.1  
    context.min_notional = -100000.0
    pipe = Pipeline()
    attach_pipeline(pipe, name='my_pipeline')
    pvol_factor = Parkinson(window_length=30)
    pvol_filter = pvol_factor.bottom(1500)

    dollar_volume= AvgDailyDollarVolumeTraded(window_length=30)
    dv_filter = dollar_volume > 100 * 10**6

    sma_10 = SimpleMovingAverage(inputs= [USEquityPricing.close], window_length=10)
    priceclose= PriceRange(window_length=1)
    price_filter= (priceclose > 10)
    
    context.account.leverage= 1
    positive_movement= (priceclose > sma_10)
    pipe.add(dv_filter, 'dv_filter')
    pipe.add(pvol_factor, 'pvol_factor')
    pipe.add(pvol_filter, 'pvol_filter')
    pipe.add(price_filter, 'price_filter')
    pipe.add(positive_movement, 'positive_movement')
    

    pipe.set_screen(price_filter & Q1500US() & positive_movement & dv_filter & pvol_filter)
    schedule_function(func=trader, date_rule=date_rules.every_day(), time_rule=time_rules.market_open())


def before_trading_start(context, data):
    # Access results using the name passed to `attach_pipeline`.
    context.results = pipeline_output('my_pipeline')
    # print results.head(5)
    context.stockpct= 0.05
    #context.stockpct= 1/(len(context.results))
    print(len(context.results))
    
def trader(context, data):
    cash = context.portfolio.cash
    leverage = context.account.leverage
    
    for stock in context.results.index:
        prices = data.history(stock, 'price', 50, '1d')
        macd = MACD(prices, fastperiod=12, slowperiod=26, signalperiod=9)
        price= data.current(stock, 'price')
        position = context.portfolio.positions[stock].amount
        # If macd crosses back over, liquidate
        if get_open_orders(stock):
            continue
        if macd < 0 and position > 0:
            order_target(stock, 0)
        # When macd crosses over to positive, full position
        elif macd > 0 and position == 0 and cash > price and leverage <1:
            order_target_percent(stock, context.stockpct)
        record(leverage=context.account.leverage*100, numofstocks= len(context.results))

def MACD(prices, fastperiod=12, slowperiod=26, signalperiod=9):
    macd, signal, hist = talib.MACD(prices,
                                    fastperiod=fastperiod,
                                    slowperiod=slowperiod,
                                    signalperiod=signalperiod)
    return macd[-1] - signal[-1]