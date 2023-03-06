from bitkub import Bitkub
import pandas as pd
from datetime import datetime
import pytz
from songline import Sendline

API_KEY = '.............................'
API_SECRET = '..............................'

token = '....................'

messenger = Sendline(token)

bitkub = Bitkub(api_key=API_KEY, api_secret=API_SECRET)
bitkub.servertime()
pd.to_datetime(bitkub.servertime(), unit='s')

posframe = pd.read_csv('config_.csv')
# df = pd.DataFrame(posframe)
# print(posframe)
ticker = pd.DataFrame(bitkub.ticker()) #sym='THB_BTC')

lim_value = 10        # ซื้อขายขั้นต่ำ 10บาท
period =    5*300*5   # 5*60*300 #

Sma_W = 5*60*24*7

def changpos(curr, buy=True):
    if buy:
        posframe.loc[posframe.Currency == curr, 'position'] = 0      #1
    # else:
    #     posframe.loc[posframe.Currency == curr, 'position'] = 0
    # posframe.to_csv('position', index=False)

def gethourldata(symbol):
    data = bitkub.tradingview(sym= symbol, int=5, 
                                        frm=(bitkub.servertime()-period), 
                                        to=bitkub.servertime())

    frame = pd.DataFrame(data)
    # frame = frame.iloc[:,:6]
    frame = frame[['t','o','h','l','c','v','s']]
    frame.columns = ['Timestamp','Open','High','Low','Close','Volume','status']
    frame['Timestamp'] = pd.to_datetime(frame['Timestamp'], unit='s').dt.tz_localize('Asia/Bangkok')
    return frame
df = gethourldata('BTC_THB')

def applytechnicals(df):
    df['FastEMA'] = df.Close.ewm(7).mean()
    df['SlowEMA'] = df.Close.ewm(25).mean()
    df['SMA_'] = df.Close.rolling(20).mean()  
    df['stddev'] = df.Close.rolling(20).std()
    df['Upper'] = df.SMA_ + 2 * df.stddev
    df['Lower'] = df.SMA_ - 2 * df.stddev    
    df['SMA_W'] = df.Close.rolling(Sma_W).mean()  
applytechnicals(df)    

def balance(coin_):
    bal = pd.DataFrame(bitkub.wallet())
    balance = bal['result'][coin_] 
    return balance

def orderhistory(crr):
    hisframe = bitkub.my_open_history(sym=crr, p=1, lmt=1)
    hisframe = pd.DataFrame(hisframe['result']) 
    orderhis = hisframe[['date','side','amount','rate','fee','credit','txn_id']]
    orderhis.to_csv('order_record.csv', mode='a', header=False, index=False)    
    order    = hisframe[['side','amount','rate']][0:1]
    amnt = order.amount
    rat  = order.rate
    order['value'] = float(amnt) * float(rat)
    print(f'{crr}',  order.set_index('side'))

def report(curr,price,amts,value,Upz,Lwz,area,svl,Cpt,arp):
    print(f' Rebalancing: Fix MM {curr} {Cpt}')
    print(f' upper: {Upz} lower: {Lwz}')
    print(f' area {area} price {price}')
    print(f' % asset: {arp}, amt: {amts}')    
    print(f' Lastvalue: {value}, P/L: {svl}')
    print('-----------------------------------')

def orderhis(crr):
    hisframe = bitkub.my_open_history(sym=crr, p=1, lmt=1)
    hisframe = pd.DataFrame(hisframe['result']) 
    order    = hisframe[['rate']][0:1].values
    return order

def trader(curr):
    # qty = posframe[posframe.Currency == curr].quantity.values[0]
    coins  = posframe[posframe.Currency == curr].coins.values[0]
    crr    = posframe[posframe.Currency == curr].crr.values[0]
    pct_   = posframe[posframe.Currency == curr].pct.values[0]
    Cpt    = posframe[posframe.Currency == curr].capital.values[0]
    Upz   = posframe[posframe.Currency == curr].upzone.values[0]
    Lwz   = posframe[posframe.Currency == curr].lowzone.values[0]

    Rte = orderhis(crr)
    df = gethourldata(curr)   
    applytechnicals(df)   
    amts = balance(coins)
    lastrow = df.iloc[-1]
    price = lastrow.Close

    area = Upz - Lwz
    value  = '%.2f'%(float(amts) * float(price))

    svl  = '%.2f'%(float((price - float(Rte)) / area ) * Cpt)
    bvl  = '%.2f'%(float((float(Rte) - price) / area ) * Cpt)      
    arp  = '%.2f'%((Upz-price)/area*100)
    pct = float(Cpt) * pct_ 

    if posframe[posframe.Currency == curr].capital.values[0]:
        report(curr,price,amts,value,Upz,Lwz,area,svl,Cpt,arp)

        if  price > Upz or price < Lwz : 
            print(f' {curr} not focus area')
            pass
        
        else :
            if price < lastrow.Lower or price > lastrow.SMA_ and float(svl) <= lim_value:

                if  float(bvl) <= lim_value:
                    pass

                elif float(bvl) >= lim_value and float(bvl) >= pct:

                    bitkub.place_bid(sym= crr, 
                                     amt= bvl, 
                                     typ='market')
                    time.sleep(3)
                    orderhistory(crr)    
                    print('______________________________________________')
                    # changpos(curr, buy=True)

                    messenger.sendtext(f' Buy {curr} : {price} : values {bvl} FMM')
            

            elif  price > lastrow.Upper or price < lastrow.SMA_ and float(bvl) <= lim_value:

                if  float(svl) <= lim_value:
                    pass

                elif float(svl) >= lim_value and float(svl) >= pct:

                        sell = '%.4f'%(float(svl) / price)

                        bitkub.place_ask(sym= crr, 
                                         amt= sell,  
                                         typ='market') 
                        time.sleep(3)
                        orderhistory(crr)                 
                        print('______________________________________________')
                        # changpos(curr, buy=True)

                        messenger.sendtext(f' Sell {curr} : {price} : values {svl} FMM')




import time

while True:
    time.sleep(60)
    for coin in posframe.Currency:
        try:
            trader(coin)
        except KeyboardInterrupt:
            print(f' error: {KeyboardInterrupt}')
            pass
        except:
            continue






#==========================================================================================================#

# token = 'YZgSPN6H2GkWpE26WaCoO8T3CV8saBTYqTj6SaBe9Lb'


# bitkub.place_bid(sym='THB_BTC', amt=1, rat=1, typ='limit')

# พารามิเตอร์:
# sym สตริงสัญลักษณ์
# amt จำนวนเงินที่คุณต้องการใช้โดยไม่มีศูนย์ต่อท้าย (เช่น 1,000.00 ไม่ถูกต้อง 1,000 ใช้ได้) default1
# rat อัตรา ลอยตัวที่คุณต้องการสำหรับคำสั่งซื้อที่ไม่มีศูนย์ต่อท้าย (เช่น 1,000.00 ไม่ถูกต้อง 1,000 ใช้ได้) default1
# typ stringประเภทคำสั่ง: ขีดจำกัดหรือdefaultขีดจำกัดของ ตลาด

# {
#   'error': 0,
#   'result': {
#     'id': 1,
#     'hash': 'fwQ6dnQWQPs4cbatF5Am2xCDP1J',
#     'typ': 'limit',
#     'amt': 1,
#     'rat': 1,
#     'fee': 2.5,
#     'cre': 2.5,
#     'rec': 0.06666666,
#     'ts': 1533834547
#   }
# }



# bitkub.place_bid_test(sym='THB_BTC', amt=1, rat=1, typ='limit', client_id='')

# พารามิเตอร์:
# sym สตริงสัญลักษณ์
# amt จำนวนเงินที่คุณต้องการใช้โดยไม่มีศูนย์ต่อท้าย (เช่น 1,000.00 ไม่ถูกต้อง 1,000 ใช้ได้) default1
# rat อัตรา ลอยตัวที่คุณต้องการสำหรับคำสั่งซื้อที่ไม่มีศูนย์ต่อท้าย (เช่น 1,000.00 ไม่ถูกต้อง 1,000 ใช้ได้) default1
# typ stringประเภทคำสั่ง: ขีดจำกัดหรือdefaultขีดจำกัดของ ตลาด
# client_id สตริง ID ของคุณสำหรับการอ้างอิง ( ไม่จำเป็น )

# {
#   'error': 0,
#   'result': {
#     'id': 1,
#     'hash': 'fwQ6dnQWQPs4cbatF5Am2xCDP1J',
#     'typ': 'limit',
#     'amt': 1,
#     'rat': 1,
#     'fee': 2.5,
#     'cre': 2.5,
#     'rec': 0.06666666,
#     'ts': 1533834547
#   }
# }








# symbols = ['THB_BTC','THB_ETH','THB_KUB','THB_XRP']





# sym_ticker = 'THB_ETH'

# df['symbol'] = 0
# df['Coin'] = 0
# df['Values'] = 0
# df['rebalance'] = 0
# print(df)


# def symbol(df):

#     df['symbol'] = Curr

# symbol(df,'THB_ETH')


# def value(df,coin,sym):

#     df['Coin'] = coin
#     df['Values'] = sym
#     print(df)
    
# value(df,'ETH',0.0061)

# for Curr in ticker:

#     print(Curr)




# for Curr in symbols:

#     if df.Currency == symbol(sym_ticker):   
#         print(df)
    


# df['symbol'] = 0
# df['Coin'] = 0
# df['Values'] = 0
# df['rebalance'] = 0
# for i in df['Currency']:
#     print([i])

# ticker = pd.DataFrame(bitkub.ticker()) #sym='THB_BTC')
# bal = pd.DataFrame(bitkub.wallet())


# symbo = 'THB_ETH' #ย้ายคอลั่มมาเป็นแถว แล้วสร้างเงื่อนไข ถ้าใดๆใน Currency == symbol  
# coin_= 'ETH'   #loop



# def balance(coin_):

#     balance = bal['result'][coin_] 
#     return balance

# symv= balance(coin_) * ticker[symbo]['last']
# print(symv)

# def value(df,sym):

#     df['Values'] = sym
#     print(sym)
# value(df,symv)





# for coin in (df.index):

    
#     if  df['Currency'][coin] == symbo and df['Fix_Values'][coin] > df['Values'][coin]:

#             rebal = df['Fix_Values'][coin] - df['Values'][coin]
        
#             df['symbol'] = symbo
#             df['Coin'] = df['coins'][coin]
#             df['rebalance'] = rebal
#             df['CashBalance'] = df['Values'][coin] - rebal

#             print(df) 
#             print(f'rebalance buy: {symbo} ',rebal)







# symbols = ['BTCUSDT','ETHUSDT','BNBUSDT','DYDXUSDT','XRPUSDT']
# posframe = pd.DataFrame(symbols)
# posframe.columns = ['Currency']
# posframe['Capital'] = 0
# posframe['Fix_Values'] = 0
# posframe['CashBalance'] = 0
# print(posframe)

# posframe.to_csv('config.csv', index= False)
# re_ = pd.read_csv('setup.csv')
# # print(re_)

# def gethourlydata(symbol):
#     frame = pd.DataFrame(client.get_historical_klines(symbol,'1h',
#                                                              '75 hours ago UTC'))
#     frame = frame[[0,4]]
#     frame.columns = ['Time','Close']
#     frame.Close = frame.Close.astype(float)
#     frame.Time = pd.to_datetime(frame.Time, unit='ms')
#     # print(frame)
#     return frame    
# temp = gethourlydata('BTCUSDT')
# print(temp)

