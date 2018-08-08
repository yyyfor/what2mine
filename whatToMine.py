import requests
import json
from bs4 import BeautifulSoup
from lxml import etree
import xlsxwriter
import datetime
# from datetime import date,datetime, timedelta
import xlrd
import math
import os
import re

'''
usage
1. Use coin.coins_info() to crawler data from what2mine
2. pass crawler data as a parameter to Excel 
3. use Excel.write_to_excel() to write data into excel. use Excel.read_excel() to read data from excel
4. the format of the file will be what2mine_20180803.xlsx
5. pass parameter to write_to_excel() and read_excel() will write or read different day excel in order to calculate SMA
e.g. 20180803 run read_excel(-1) will read excel from 20180802
6. (To be modified)SMA.gpu__and_profit will calculate # of GPU change in 7 days and proift change in 30days
7. TODO: 1. write SMA data to excel. 2. catch error 3. logs
'''

hashrate=dict()
hashrate['Ethash']='35 Mh/s'					
hashrate['Zhash']='56 h/s'						
hashrate['PHI1612']='33 Mh/s'						
hashrate['CryptoNightHeavy']='960 h/s'					
hashrate['CryptoNightV7']='850 h/s'						
hashrate['Equihash']='685 h/s'						
hashrate['Lyra2REv2']='640000 kh/s'					
hashrate['NeoScrypt']='1400 kh/s'							
hashrate['TimeTravel10']='30 Mh/s'							
hashrate['X16R']='15 Mh/s'								
hashrate['Lyra2z']='3 Mh/s'								
hashrate['PHI2']='6 Mh/s'					
hashrate['Xevan']='5.3 Mh/s'

urls = ['https://whattomine.com/coins.json', 'https://api.coinmarketcap.com/v2/ticker/', 'https://whattomine.com/']

columns = ['coin','Algorithm','Price','Market Cap', 'Volumn', 'Diffculty','Hashrate','Network Hashrate','Rev','Profit','Cost']

units = {'h/s':1, 'Mh/s':6,'kh/s':3, 'Gh/s':9,'Th/s':12}

what2mine_directory = '/data/whatToMine/excel'

class Download(object):

    def website_data(self , urls):
        #retreive what2mine json data
        response = requests.get(urls[0])
        data = response.json()
        #retreive marketcap data
        # reponse_coinmarket = requests.get(urls[1]).json()
        # data_coinmarket = reponse_coinmarket['data']
        #crarwler what2mine website
        request = requests.get(urls[2])
        data_what2mine = request.content

        nicehash = Nicehash()
        coinlib = CoinLib()
        #anaylyze coin price
        # what2mine = What2mine(nicehash,coinlib)
        
        return data,  data_what2mine

class Coin(object):

    coin_names = []
    algorithms = []
    market_caps = []
    prices = []
    difficulties = []
    hashrates = []
    nethashs = []
    volumns = []
    revenues = []
    profits = []
    costs = []

    def __init__(self,what2mine):
        self.what2mine = what2mine

    #get price from coinmarket
    def find_price(self,coin_name,coin_symbol):
        return self.what2mine.price(coin_symbol,coin_name)
    
    def diffculty(self,d):
        if d == 1:
            return '-'
        else:
            return d

    #get coins info from what2mine website
    def coins_info(self):
        downlad = Download()
        data,  data_what2mine = downlad.website_data(urls)
        coins = data['coins']
        parser = Parser()
        for coin,values in coins.items():
            self.coin_names.append(coin)
            self.algorithms.append(values['algorithm'])
            self.market_caps.append(values['market_cap'])
            self.prices.append('$' + str(self.find_price(coin,values['tag'])))
            self.difficulties.append(self.diffculty(values['difficulty']))
            self.hashrates.append(hashrate[values['algorithm']])
            Nethash, volumn, revenue, profit, cost = parser.parse(data_what2mine, coin)
            self.nethashs.append(Nethash)
            self.volumns.append(volumn)
            self.revenues.append(revenue)
            self.profits.append(profit)
            self.costs.append(cost)
        return [self.coin_names, self.algorithms,self.prices, self.market_caps, self.volumns, self.difficulties, self.hashrates, self.nethashs, self.revenues, self.profits, self.costs]

class Parser(object):

    #convert '$2.90' to '2.9' in order to calculate cost
    def money_to_num(self, money):
        return money.split('$')[1]
    
    def parse(self,contents,coin):
        soup = BeautifulSoup(contents,'lxml')
        trs = soup.find_all('tr')
        for tr in trs:
            coin_tag = tr.find('div',attrs = {'style':'margin-left: 50px'})
            ##website has 2 empty columns. ignore 
            if not isinstance(coin_tag, type(None)):
                #Ethereum Classic and Ethereum both has name "Ethereum"
                if coin == "Ethereum":
                    coin = "ETH"
                if(coin_tag.text.find(coin) != -1):
                    #Nethash
                    Nethash = tr.find('div',class_='small_text').text.split('\n')[1]
                    #volumn
                    volumn = str.strip(tr.find('strong').findNext('strong').text)
                    #revenue
                    revenue = tr.find_all('td')[7].text.split('\n')[1]
                    #profit
                    profit = tr.find_all('td')[7].text.split('\n')[3]
                    #cost
                    cost = round(float(self.money_to_num(revenue))-float(self.money_to_num(profit)),2)
                    cost_str = '$' + str(cost)
                    break

        return Nethash, volumn, revenue, profit, cost_str

class Time(object):

    def today(self):
        now = datetime.datetime.now()
        return now

    def file_name(self,days):
        suffix = datetime.date.strftime(self.day_gap(days),"20%y%m%d")
        _file_name =  'what2mine_' + suffix + '.xlsx'
        return _file_name

    def day_gap(self,num):
        if num > 0:
            d = self.today() + datetime.timedelta(days=num)
        else:
            d = self.today() - datetime.timedelta(days=abs(num))
        return d
    
class Excel(object):

    data_set = []
    time = Time()

    def __init__(self,data=None):
        self.data_set = data

    def write_to_excell(self,days=0):

        #create directory if not exists
        if not os.path.exists(what2mine_directory):
            os.makedirs(what2mine_directory)

        #enter the directory
        os.chdir(what2mine_directory)
        
        # Create a workbook and add a worksheet.
        workbook = xlsxwriter.Workbook(self.time.file_name(days))
        worksheet = workbook.add_worksheet()

        # Start from the first cell. Rows and columns are zero indexed.
        row = 0
        col = 0

        # Iterate over the data and write it out row by row.
        for item in (columns):
            worksheet.write(row, col, item)
            col += 1

        row = 1
        col = 0

        for items in self.data_set:
            for item in items:
                worksheet.write(row, col, item)
                row += 1
            col += 1
            row = 1  

        workbook.close()    
    
    def read_excel(self,days=0):
        #if file not exists, return none
        result = dict()
        try:
            os.chdir(what2mine_directory)
            data = xlrd.open_workbook(self.time.file_name(days))
            table = data.sheet_by_name("Sheet1")
            nrows = table.nrows
            for i in range(1,nrows):  
                rows  = table.row_values(i) #rows data in array
                map = dict()
                for j in range(1,len(rows)):
                    map.update({columns[j]:rows[j]})
                result.update({rows[0]:map})
        except:
            return None
        return result

class SMA(object):
    
    def gpu__and_profit(self):
        
        excel = Excel()
        data_today = excel.read_excel()
        data_7days_before = excel.read_excel(-7)
        data_30days_before = excel.read_excel(-30)

        for key,value in data_today.items():
            #today's gpu number
            GPU_number = self.cal_gpu_numbers(value)
            #7 day before's gpu number
            old_GPU_number = self.cal_gpu_numbers(data_7days_before[key])
            #today's profit
            profit = value['Profit']
            old_profit = data_30days_before[key]['Profit']
            profit_change = '$' + (float(profit.split('$')[2]) - float(old_profit.split('$')[2]))
            print (profit_change)
            gpu_change = (GPU_number - old_GPU_number) / GPU_number
            return gpu_change, profit_change

    def cal_gpu_numbers(self,data):
        hashrate = data['Hashrate']
        total_hashrate = data['Network Hashrate']
        gpu_number = self.div(total_hashrate) / self.div(hashrate)
        return gpu_number

    #calculate hashrate in digital
    def div(self,hashrate):
        result = hashrate.split(' ')
        number = float(result[0])
        index = result[1]
        return number * float(math.pow(10,units.get(index)))
        
class Nicehash():

    nicehash_json = dict()
    nicehash_algo = {'Nicehash-CNHeavy':'31','Nicehash-Lyra2REv2':'14','Nicehash-CNV7':'30','Nicehash-NeoScrypt':'8',
'Nicehash-X16R':'33','Nicehash-Equihash':'24','Nicehash-Lyra2z':'14'}

    def __init__(self):
        self.nicehash_json = self.nicehash_data()

    #get nicehash data from nicehash api
    def nicehash_data(self):
        nicehash_url = 'https://api.nicehash.com/api'
        parameters = {'method':'stats.global.current','location':'1'}
        response = requests.get(url = nicehash_url, params = parameters)
        return response.json()['result']['stats']

    #find nicehash coin price using algo_num
    def find_nicehash_price(self, algo):
        algo_num = self.nicehash_algo[algo]
        for item in self.nicehash_json:
            if(item['algo'] == int(algo_num)):
                return item['price']
        return None

class CoinAPI():
    #coinAPI
    data = dict()
    prices = dict()
    coin_symbols = []

    def __init__(self):
        url = 'https://rest.coinapi.io/v1/assets'
        price_url = 'https://rest.coinapi.io/v1/exchangerate/'
        headers = {'X-CoinAPI-Key' : 'ADBEB874-C605-41A7-ADAE-17454A2112BA'}
        self.data = requests.get(url, headers=headers)
        self.prices = requests.get(price_url, headers=headers)

#23e61774-41dc-49e0-8603-36034ea9ef7a
#7ed50e01-4096-45d0-8e06-972c16622133
class CoinMarketCap():

    symbols = dict()
    names = dict()
    prices = []

    def __init__(self):
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        header = {'X-CMC_PRO_API_KEY':'7ed50e01-4096-45d0-8e06-972c16622133'}
        param = {'limit':'2000'}
        r = requests.get(url, params = param, headers = header)
        if r.status_code == 200:
            data = r.json()['data']
        else:
            print (r.json()['status']['error_message'])

        for item in data:
            self.symbols.update({item['symbol'].upper():item['quote']['USD']['price']})
            self.names.update({item['name']:item['quote']['USD']['price']})
        print ('get data from coinmarketcap')

class CoinLib():

    #api key ec7e6e08c7082ce0
    def price(self,symbol):
        params = {'key':'ec7e6e08c7082ce0','symbol':symbol}
        url = 'https://coinlib.io/api/v1/coin'
        r = requests.get(url = url,params=params)
        if r.status_code == 200:
            return r.json()['price']
        else:
            return None


class What2mine():

    def __init__(self,nicehash,coinlib):
        self.nicehash = nicehash
        # self.coinMarketCap = coinMarketCap
        self.coinlib = coinlib

    def price(self,tag,name):
        if re.search('Nicehash-Ethash',name, re.I):
            return None
            #return None

        elif re.search('Nicehash-',name, re.I):
            return self.nicehash.find_nicehash_price(name)
            #return self.nicehash.find_nicehash_price(key)

        else:
            return self.coinlib.price(tag)

if __name__ == "__main__":
    nicehash = Nicehash()
    coinlib = CoinLib()
    w = What2mine(nicehash,coinlib)
    coin = Coin(w)
    # excel = Excel(None)
    excel = Excel(coin.coins_info())
    excel.write_to_excell()
    # excel.write_to_excell()
    # sma = SMA()
    # sma.gpu__and_profit()


