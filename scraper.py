import requests
import urllib.request
import time, json, os, traceback
from json import JSONDecodeError
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from time import sleep
from collections import deque

class StockTwitsAPIScraper:
    def __init__(self, symbol, date, maxId):
        self.symbol = symbol
        self.link = "https://api.stocktwits.com/api/2/streams/symbol/{}.json?".format(symbol)
        self.targetDate = date
        self.tweets = []
        self.reqeustQueue = deque()
        self.maxId = maxId
        self.initDir()

    def setLimits(self, size, duration):
        self.size = size
        self.duration = duration
        self.requestInterval = duration // size + 1 if duration % size else duration // size

    # create directions if they don't exist
    def initDir(self):
        if not os.path.isdir("stocks"):
            os.mkdir("stocks")
        if not os.path.isdir("stocks/{}".format(self.symbol)):
            os.mkdir("stocks/{}".format(self.symbol))

    # write tweets we get and the ID of the last tweet in case system break down
    def writeJson(self):
        if self.tweets:
            self.maxId = self.tweets[-1]["id"]
            fileName = "stocks/{}/{}.json".format(self.symbol, self.maxId)
            with open(fileName, "w") as f:
                json.dump(self.tweets, f)
    
    def getCurrentUrl(self):
        return self.link + "max={}".format(self.maxId)

    # request manager
    # can't exceed 200 requests within an hour
    def requestManager(self):
        if len(self.reqeustQueue) == self.size:
            now = datetime.now()
            firstRequest = self.reqeustQueue.popleft()
            if now < firstRequest + timedelta(seconds=self.duration):
                timeDiff = firstRequest - now
                waitTime = timeDiff.total_seconds() + 1 + self.duration                
                print("Reach request limit, wait for {} seconds.".format(waitTime))
                sleep(waitTime)

    def getMessages(self, url):
        self.requestManager()

        response = requests.get(url)
        self.reqeustQueue.append(datetime.now())
        try:
            data = json.loads(response.text)
        except JSONDecodeError:
            if "Bad Gateway" in response.text:
                print("Just a Bad Gateway, wait for 1 minute.")
                sleep(60)
                return True
            print(len(self.reqeustQueue))
            print(self.reqeustQueue[0], datetime.now())
            print(url)
            print(response.text)
            print(traceback.format_exc())
            raise Exception("Something worong with the response.")
        if data and data["response"]["status"] == 200:
            data["cursor"]["max"]
            for m in data["messages"]:
                record = {}            
                createdAt = datetime.strptime(m["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                if createdAt < self.targetDate:
                    return False
                record["id"] = m["id"]
                record["text"] = m["body"]
                record["time"] = createdAt.timestamp()
                record["sentiment"] = m["entities"]["sentiment"]["basic"] if m["entities"]["sentiment"] else ""
                self.tweets.append(record)
        else:
            print(response.text)        
        return True

    def getTweetsAndWriteToFile(self):        
        if not self.getMessages(self.getCurrentUrl()):
            return False
        self.writeJson()
        print("Scrap {} tweets starting from {}.".format(len(self.tweets), self.maxId))
        self.tweets.clear()
        sleep(self.requestInterval)
        return True

    def scrapTweets(self):        
        try:
            doScrap = True
            while doScrap:
                doScrap = self.getTweetsAndWriteToFile()
        except Exception:
            print(traceback.format_exc())

symbol = input("Enter stock symbol: ")
print("This scraper scraps tweets backward.\n\
The ID you put in belongs the most recent tweet you're goint go scrap.\n\
And the scraper will keep going backward to scrap older tweets.")
maxId = input("Enter the starting tweet ID: ")
targetDate = input("Enter the earlest date (mmddyyyy): ")
print("You can only send 200 requests to StockTwits in an hour.")
requestLimit = input("Enter the limit of number of requests within an hour: ")

scraper = StockTwitsAPIScraper(symbol, datetime.strptime(targetDate, "%m%d%Y"), int(maxId))
scraper.setLimits(int(requestLimit), 3600)
scraper.scrapTweets()