from quantopian.pipeline import Pipeline
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.filters import Q3000US
from quantopian.pipeline.factors import SimpleMovingAverage
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data import morningstar
from quantopian.pipeline import CustomFactor
import talib
import math
import numpy as np
import pandas as pd
class PriceRange(CustomFactor):  
    inputs = [USEquityPricing.close]  
    def compute(self, today, assets, out, close):  
        out[:] = close[-1]  

class Parkinson(CustomFactor):    
    inputs = [USEquityPricing.high, USEquityPricing.low]
    def compute(self, today, assets, out, high, low):
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
    context.stockpct= 0.05
    context.lowrsi= 30
    context.highrsi= 70

    pipe = Pipeline()
    attach_pipeline(pipe, name='my_pipeline')
 

    sma_30 = SimpleMovingAverage(inputs= [USEquityPricing.close], window_length=30)
    sma_10 = SimpleMovingAverage(inputs= [USEquityPricing.close], window_length=10)
    sma_5 = SimpleMovingAverage(inputs= [USEquityPricing.close], window_length=5)
    
    priceclose= PriceRange(window_length=1)
    price_filter= (priceclose > 10)    
    
    dollar_volume= AvgDailyDollarVolumeTraded(window_length=30)
    dv_filter = dollar_volume > 100 * 10**6
    
    context.account.leverage= 1
    
    positive_movement= (sma_5 > sma_10)
    positive_movement_long= (sma_10 > sma_30)
    
    pipe.add(dv_filter, 'dv_filter')
    pipe.add(price_filter, 'price_filter')
    pipe.add(positive_movement, 'positive_movement')
    pipe.add(positive_movement_long, 'positive_movement_long')
    
    pipe.set_screen(price_filter & dv_filter & positive_movement & positive_movement_long)
    schedule_function(func=trader, date_rule=date_rules.every_day(), time_rule=time_rules.market_open(hours=0, minutes=5))
    schedule_function(func=liquidate, date_rule=date_rules.every_day(), time_rule=time_rules.market_open(hours=0, minutes=1))

def before_trading_start(context, data):
    context.results = pipeline_output('my_pipeline')
    print(context.results.index)    
def trader(context, data):
    cash = context.portfolio.cash
    leverage = context.account.leverage
    prices = data.history(context.results.index, 'price', 50, '1d')
    rsis = {}
    for stock in context.results.index:
        rsi14 = talib.RSI(prices[stock], timeperiod=14)[-1]
        rsis[stock] = rsi14
        price= data.current(stock, 'price')
        position = context.portfolio.positions[stock].amount
        # If macd crosses back over, liquidate
        if get_open_orders(stock):
            continue
        
        if rsi14 > context.highrsi and position > 0:
            order_target(stock, 0)
        # When macd crosses over to positive, full position
        
        elif rsi14 < context.lowrsi and position == 0 and cash > price and leverage <1:
            order_target_percent(stock, context.stockpct)
        record(leverage=context.account.leverage, numofstocks= len(context.results))
        
def liquidate(context, data):
    prices = data.history(context.portfolio.positions.keys(), 'price', 50, '1d')
    rsis = {}
    for stock in context.portfolio.positions:
        rsi14 = talib.RSI(prices[stock], timeperiod=14)[-1]
        rsis[stock] = rsi14       
        if rsi14 >= 70:
            order_target(stock, 0)
            
def RSI(df, n):  
    i = 0  
    UpI = [0]  
    DoI = [0]  
    while i + 1 <= df.index[-1]:  
        UpMove = df.get_value(i + 1, 'High') - df.get_value(i, 'High')  
        DoMove = df.get_value(i, 'Low') - df.get_value(i + 1, 'Low')  
        if UpMove > DoMove and UpMove > 0:  
            UpD = UpMove  
        else: UpD = 0  
        UpI.append(UpD)  
        if DoMove > UpMove and DoMove > 0:  
            DoD = DoMove  
        else: DoD = 0  
        DoI.append(DoD)  
        i = i + 1  
    UpI = pd.Series(UpI)  
    DoI = pd.Series(DoI)  
    PosDI = pd.Series(pd.ewma(UpI, span = n, min_periods = n - 1))  
    NegDI = pd.Series(pd.ewma(DoI, span = n, min_periods = n - 1))  
    RSI = pd.Series(PosDI / (PosDI + NegDI), name = 'RSI_' + str(n))  
    df = df.join(RSI)  
    return df