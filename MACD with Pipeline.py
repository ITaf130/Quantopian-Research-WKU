from quantopian.pipeline import Pipeline
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.factors import SimpleMovingAverage
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data import morningstar

import talib
import numpy as np
import pandas as pd

def initialize(context):
    context.date= None
    pipe= Pipeline()
    sma_10 = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=10)
    prices_over_10 = (sma_10 > 10)
    pipe.add(sma_10, 'sma_10')
    pipe.set_screen(prices_over_10)
    schedule_function(func=get_stocks, date_rule=date_rules.month_start(days_offset=0), time_rule=time_rules.market_open(hours=0, minutes=1))
def get_stocks(context, data):
    context.results= pipeline_output('my_pipeline')
    print(context.results)
    update_universe('my_pipeline')
    

def handle_data(context, data):
    todays_date= get_datetime().date()
    if todays_date== context.date:
        return
    
    context.date= todays_date    
    prices = history(50, '1d', 'price')
    #Need to experiment with different periods
    macd = prices.apply(MACD, fastperiod=12, slowperiod=26, signalperiod=9)
    for stock in context.results.index:
        position = context.portfolio.positions[stock].amount
        #If macd crosses back over, liquidate
        if macd[stock] < 0 and position > 0:
            order_target(stock, 0)
        #When macd crosses over to positive, full position
        elif macd[stock] > 0 and position == 0:
            order_target_percent(stock, context.stockpct) 
        record(leverage=context.account.leverage)
def MACD(prices, fastperiod=12, slowperiod=26, signalperiod=9):
    macd, signal, hist = talib.MACD(prices, 
                                    fastperiod=fastperiod, 
                                    slowperiod=slowperiod, 
                                    signalperiod=signalperiod)
    return macd[-1] - signal[-1]