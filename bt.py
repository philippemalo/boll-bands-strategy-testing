import backtrader
from datetime import datetime, timedelta
from ccxt.ftx import ftx
import os
import pandas as pd
import math

# Getting data from FTX
exchange = ftx()

symbol : str = 'BTC/USDT'
timeframe : str = "4h"
utc_now : datetime = datetime.now() # Don't use utcnow()
cutoff = utc_now - timedelta(hours=1)
cutoff = int(cutoff.timestamp()) * 1000
since = 1654833600000

candles = exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=since)
print(candles)

# Candles data to pandas dataframe
divisor : int = 1000 if os.name=='nt' else 1

candles = pd.DataFrame(candles)
candles.rename(columns={0: "timestamp", 1: "open", 2: "high", 3: "low", 4: "close", 5: "volume"}, inplace=True)
candles['datetime'] = candles['timestamp'].apply(lambda ts : datetime.fromtimestamp(int(ts)/divisor))
candles['date'] = candles['timestamp'].apply(lambda ts : datetime.fromtimestamp(int(ts)/divisor).date())
candles.set_index(['datetime'], inplace=True)

# COMPUTING UPPER AND LOWER BOLLINGER BANDS
candles['tp'] = (candles['high']+candles['low']+candles['close'])/3
candles['std'] = candles['tp'].rolling(20).std(ddof=0)
candles['ma-tp'] = candles['tp'].rolling(20).mean()
candles['bolu'] = candles['ma-tp'] + 2*candles['std']
candles['bold'] = candles['ma-tp'] - 2*candles['std']
candles['priceBolu'] = (candles['high'] - candles['bolu'])/candles['bolu']
candles['priceBold'] = (candles['low'] - candles['bold'])/candles['bold']

# Sanitizing...
candles.reset_index(drop=False, inplace=True)
candles.drop(['timestamp', 'tp', 'std', 'ma-tp', 'bolu', 'bold', 'date'], axis=1, inplace=True)
print(candles)

cerebro = backtrader.Cerebro()

cerebro.getbroker().set_cash(25000)

print(cerebro.getbroker().get_cash())

data = backtrader.feeds.PandasData(dataname=candles)

class PandasDataExt(backtrader.feeds.PandasData):
    lines = ('priceBolu', 'priceBold')
    params = (
        ('priceBolu', 6),
        ('priceBold', 7)
        )

# data = bt.feeds.PandasData(dataname=candles)
data = PandasDataExt(
    dataname=candles,
    datetime=0,
    open=1,
    high=2,
    low=3,
    close=4,
    volume=5,
    priceBolu=6,
    priceBold=7
)
cerebro.adddata(data)

class BOLUBOLDStrategy(backtrader.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

    def next(self):
        priceBolu : float = self.data0_priceBolu[0]
        priceBold : float = self.data0_priceBold[0]
        open: float = self.data0_open[0]

        self.log(f"priceBolu: {priceBolu}, priceBold: {priceBold}")

        if not math.isnan(self.data0_priceBolu[0]):
            # if price extends downwards of more than 3% under lower bollinger band, buy.
            if priceBold<-0.03:
                self.log(f"Send BUY order, price-bold: {priceBold}")
                self.buy()
            # if price extends upwards of more than 3% above upper bollinger band, sell.
            elif priceBolu>0.03:
                self.log(f"Send SELL order, price-bolu: {priceBolu}")
                self.sell()



cerebro.addstrategy(BOLUBOLDStrategy)

cerebro.run()
finalPortVal = cerebro.getbroker().get_value()
print(finalPortVal)