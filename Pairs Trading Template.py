import numpy as np
import pandas
import statsmodels
import quantopian.pipeline
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
def initialize(context):
    set_commission(commission.PerShare(cost=0.001, min_trade_cost=1))
    context.stock1= sid(17508)
    context.stock2= sid(46637)
    context.threshold = 1
    context.security_list = (context.stock1, context.stock2)
    
    context.low = False
    context.high = False
    schedule_function(rebalance, date_rule=date_rules.every_day(), time_rule=time_rules.market_close(hours=1))

   

def rebalance(context, data):
    
    if len(get_open_orders()) > 0:
        return
    s1 = context.stock1
    s2 = context.stock2
    p30 = data.history(context.security_list, 'price', 30, '1d')
    p5 = p30.iloc[-5:]
    # Get the 30 day mavg
    m30 = np.mean(p30[s1] - p30[s2])
    # Get the std of the last 30 days
    stddev = np.std(p30[s1] - p30[s2])
    
    
    # Current diff = 5 day mavg
    m5 = np.mean(p5[s1] - p5[s2])
    
    # zscore
    if stddev > 0:
        zscore = (m5 - m30)/stddev
    else:
        zscore=0
    if zscore >= context.threshold and not context.high and     all(data.can_trade(context.security_list)):
        order_target_percent(s1, -0.5) # short top
        order_target_percent(s2, 0.5) # long bottom
        context.high = True
        context.low = False
    elif zscore <= -context.threshold and not context.low and all(data.can_trade(context.security_list)):
        order_target_percent(s1, 0.5) # long top
        order_target_percent(s2, -0.5) # short bottom
        context.high = False
        context.low = True
    #Order Cancellation
    elif abs(zscore) < 0.25  and all(data.can_trade(context.security_list)):
        order_target_percent(s1, 0)
        order_target_percent(s2, 0)
        context.high = False
        context.low = False
        
    elif zscore > context.threshold and abs(zscore) > 1.25 and all(data.can_trade(context.security_list)):
        order_target_percent(s1, 0)
        order_target_percent(s2, 0)
        context.high = False
        context.low = False
    elif zscore < -context.threshold and abs(zscore) > 1.25 and all(data.can_trade(context.security_list)):
        order_target_percent(s1, 0)
        order_target_percent(s2, 0)
        context.high = False
        context.low = False
    record('zscore', zscore, lev=context.account.leverage, faroprice=data[17508].price, fplprice=data[46637].price)