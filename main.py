import requests
import time
import itertools
import digitalio
import busio
import board
from adafruit_epd.epd import Adafruit_EPD
from adafruit_epd.ssd1680 import Adafruit_SSD1680
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# setting up e-ink bonnet
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)
srcs = None

display = Adafruit_SSD1680(122, 250, spi, cs_pin=ecs, dc_pin=dc, sramcs_pin=srcs, rst_pin=rst, busy_pin=busy)
small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
medium_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
large_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

display.rotation = 1

# which stops to be used, these can be found at https://www.metrotransit.org/nextrip or on Google Maps by clicking on stop
Stops = ('170', '20048', '16839', '16837')

def getAPI(stopID):
    url = 'https://svc.metrotransit.org/NexTrip/'
    global response
    response = []
    for x in stopID:
        response.append(requests.get(url + x + '?format=json').json())
    response = list(itertools.chain.from_iterable(response))
    return response

def updateList(rawList):
    updatedList = []
    currentTime = round(time.time())
    i=0
    if bool(rawList) == False:
        updatedList.append('No More Buses')
    else:
        while i < len(rawList) and i < 4:
            updatedList.append((round(((int(rawList[i]['DepartureTime'][6:19]) / 1000) - currentTime) / 60)))
            i+=1
    return updatedList

def update_display(updatedList):
    response = getAPI(Stops)
    updatedList = updateList(response)

    #to filter out the exact route and direction I wanted as there are multiple routes that stop at each stop
    NB = updateList(list(filter(lambda c: c['RouteDirection'] == 'NB' and c['Route'] == '4', response)))
    SB = updateList(list(filter(lambda c: c['RouteDirection'] == 'SB' and c['Route'] == '4', response)))
    EB = updateList(list(filter(lambda c: c['RouteDirection'] == 'EB' and c['Route'] == '21', response)))
    WB = updateList(list(filter(lambda c: c['RouteDirection'] == 'WB' and c['Route'] == '21', response)))

    NB_Times = '  '.join([str(elem) for elem in NB])
    SB_Times = '  '.join([str(elem) for elem in SB])
    EB_Times = '  '.join([str(elem) for elem in EB])
    WB_Times = '  '.join([str(elem) for elem in WB])

    busRoutes = ['#4 N', '#4 S', '#21 E', '#21 W']
    busTimes = [NB_Times, SB_Times, EB_Times, WB_Times]

    display.fill(Adafruit_EPD.WHITE)
    image = Image.new('RGB', (display.width, display.height), color=WHITE)
    draw = ImageDraw.Draw(image)
    now = datetime.now()
    timeText = now.strftime('%I:%M').lstrip('0').replace(' 0', ' ')
    
    #draw time and location
    (font_width, font_height) = small_font.getsize(timeText)
    draw.text((display.width - font_width -3, 5), timeText, font = small_font, fill = BLACK)
    (font_width, font_height) = small_font.getsize('Lake & Lyndale')
    draw.text((display.width - font_width -105, 5), 'Lake & Lyndale', font = small_font, fill = BLACK)

    # draw route
    route_multiplier = 4
    for route in busRoutes:
        (font_width, font_height) = large_font.getsize(route)
        draw.text((5, display.height - font_height * route_multiplier), route, font=large_font, fill=BLACK)
        route_multiplier -= 1

    #draw times
    time_multiplier = 4.7
    for time in busTimes:
        (font_width, font_height) = medium_font.getsize(time)
        draw.text((display.width - font_width -5, display.height -font_height * time_multiplier,), time, font=medium_font, fill=BLACK)
        time_multiplier -= 1.25
   
    display.image(image)
    display.display()
    
    # run every 60 seconds                                               
while True:
    response = getAPI(Stops)
    updatedList = updateList(response)
    if len(updatedList) >0:
        update_display(updatedList)
    else:
        pass
    time.sleep(60)

    # set up a cron job to run it every morning and kill it every night
