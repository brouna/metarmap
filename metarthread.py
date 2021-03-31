#!/usr/bin/env python3

import urllib.request
import xml.etree.ElementTree as ET
import board
import neopixel
from time import sleep
import datetime
import threading
import logging
try:
	import displaymetar
except ImportError:
	displaymetar = None

# metar.py script iteration 1.4.2

# ---------------------------------------------------------------------------
# ------------START OF CONFIGURATION-----------------------------------------
# ---------------------------------------------------------------------------

# NeoPixel LED Configuration
LED_COUNT		= 50			# Number of LED pixels.
LED_PIN			= board.D18		# GPIO pin connected to the pixels (18 is PCM).
LED_BRIGHTNESS		= 0.5			# Float from 0.0 (min) to 1.0 (max)
LED_ORDER		= neopixel.GRB		# Strip type and colour ordering

COLOR_VFR		= (255,0,0)		# Green
COLOR_VFR_FADE		= (125,0,0)		# Green Fade for wind
COLOR_MVFR		= (0,0,255)		# Blue
COLOR_MVFR_FADE		= (0,0,125)		# Blue Fade for wind
COLOR_IFR		= (0,255,0)		# Red
COLOR_IFR_FADE		= (0,125,0)		# Red Fade for wind
COLOR_LIFR		= (0,125,125)		# Magenta
COLOR_LIFR_FADE		= (0,75,75)		# Magenta Fade for wind
COLOR_CLEAR		= (0,0,0)		# Clear
COLOR_LIGHTNING		= (255,255,255)		# White

# ----- Blink/Fade functionality for Wind and Lightning -----
# Do you want the METARMap to be static to just show flight conditions, or do you also want blinking/fading based on current wind conditions
ACTIVATE_WINDCONDITION_ANIMATION = True		# Set this to False for Static or True for animated wind conditions
#Do you want the Map to Flash white for lightning in the area
# ACTIVATE_LIGHTNING_ANIMATION = True		# Set this to False for Static or True for animated Lightning
# Fade instead of blink
# FADE_INSTEAD_OF_BLINK	= False			# Set to False if you want blinking
# Blinking Windspeed Threshold
WIND_BLINK_THRESHOLD	= 25			# Knots of windspeed
ALWAYS_BLINK_FOR_GUSTS	= False			# Always animate for Gusts (regardless of speeds)
# Blinking Speed in seconds
BLINK_SPEED		= 2.0			# Float in seconds, e.g. 0.5 for half a second
# Total blinking time in seconds.

# How often to refresh weather - suggest 30 minutes
REFRESH_TIME_SECONDS = 1800 #30 minutes = 1800s

# ----- Daytime dimming of LEDs based on time of day or Sunset/Sunrise -----
ACTIVATE_DAYTIME_DIMMING = True		# Set to True if you want to dim the map after a certain time of day
BRIGHT_TIME_START	= datetime.time(7,0)	# Time of day to run at LED_BRIGHTNESS in hours and minutes
DIM_TIME_START		= datetime.time(19,0)	# Time of day to run at LED_BRIGHTNESS_DIM in hours and minutes
LED_BRIGHTNESS_DIM	= 0.1			# Float from 0.0 (min) to 1.0 (max)

USE_SUNRISE_SUNSET 	= True			# Set to True if instead of fixed times for bright/dimming, you want to use local sunrise/sunset
LOCATION 		= "Boston"		# Nearby city for Sunset/Sunrise timing, refer to https://astral.readthedocs.io/en/latest/#cities for list of cities supported

# ----- External Display support -----
ACTIVATE_EXTERNAL_METAR_DISPLAY = True		# Set to True if you want to display METAR conditions to a small external display
DISPLAY_ROTATION_SPEED = 5.0				# Float in seconds, e.g 2.0 for two seconds
FAST_BLINK_DISPLAYED_STATION = True			# If true, the station shown on the display blinks fast
FAST_BLINK_SPEED = 0.1						#...this fast

DONTSTOP = -1							# use this to tell the STOPFLAG not to signal any stoppages; just needs to be a number outside the thread range
STOPFLAG = DONTSTOP

# ---------------------------------------------------------------------------
# ------------END OF CONFIGURATION-------------------------------------------
# ---------------------------------------------------------------------------
def initialize_logging():
	logging.basicConfig(filename='metar.log', level=logging.INFO)

def initialize_display_and_leds():
	# Initialize the LED strip
	bright = BRIGHT_TIME_START < datetime.datetime.now().time() < DIM_TIME_START
	logging.info ("Wind animation: %s", str(ACTIVATE_WINDCONDITION_ANIMATION))
	logging.info ("Daytime Dimming: %s", str(ACTIVATE_DAYTIME_DIMMING))
	logging.info(" using Sunrise/Sunset" if USE_SUNRISE_SUNSET and ACTIVATE_DAYTIME_DIMMING else "")
	logging.info("External Display: %s " , str(ACTIVATE_EXTERNAL_METAR_DISPLAY))

	p = neopixel.NeoPixel(LED_PIN, LED_COUNT, brightness = LED_BRIGHTNESS_DIM if (ACTIVATE_DAYTIME_DIMMING and bright == False) else LED_BRIGHTNESS, pixel_order = LED_ORDER, auto_write = False)

	# Start up external display output
	disp = None
	if displaymetar is not None and ACTIVATE_EXTERNAL_METAR_DISPLAY:
		disp = displaymetar.startDisplay()
		displaymetar.clearScreen(disp)

	return(p,disp)


def blinkme(pixelnum,color,time,blinkrate):    #time = time in seconds to blink for ; blinkrate = time in seconds of a blink cycle (<< time)
        numblinks = int(time/blinkrate)
        for i in range(numblinks):
                pixels[pixelnum]=COLOR_CLEAR
                pixels.show()
                sleep(blinkrate/2)
                pixels[pixelnum]=color
                pixels.show()
                sleep(blinkrate/2)
                # check for stopping flag for this pixel
                global STOPFLAG
                if STOPFLAG == pixelnum:
                	break
        return

''' Illustration of threading the above function
#prepare thread
x = threading.Thread(target=blinkme, args=(2,COLOR_MVFR,5,.1))
x.start()
y = threading.Thread(target=blinkme, args=(3,COLOR_LIFR,5,1))
y.start()
# to stop the thread, set STOPFLAG to the pixel number to stop, then join the thread
'''

def calc_daytime():
# Figure out sunrise/sunset times if astral is being used
	try:
        	import astral
	except ImportError:
        	astral = None

	if astral is not None and USE_SUNRISE_SUNSET:
		try:
			# For older clients running python 3.5 which are using Astral 1.10.1
			ast = astral.Astral()
			try:
				city = ast[LOCATION]
			except KeyError:
				logging.error("Error: Location not recognized, please check list of supported cities and reconfigure")
			else:
				print(city)
				sun = city.sun(date = datetime.datetime.now().date(), local = True)
				BRIGHT_TIME_START = sun['sunrise'].time()
				DIM_TIME_START = sun['sunset'].time()
		except AttributeError:
			# newer Raspberry Pi versions using Python 3.6+ using Astral 2.2
			import astral.geocoder
			import astral.sun
			try:
				city = astral.geocoder.lookup(LOCATION, astral.geocoder.database())
			except KeyError:
				logging.error("Error: Location not recognized, please check list of supported cities and reconfigure")
			else:
				logging.info("%s", city)
				sun = astral.sun.sun(city.observer, date = datetime.datetime.now().date(), tzinfo=city.timezone)
				BRIGHT_TIME_START = sun['sunrise'].time()
				DIM_TIME_START = sun['sunset'].time()
	return

def get_airport_list():
		# Read the airports file to retrieve array of airports and use as order for LEDs
	with open("/MetarMap/airports") as f:
		airports = f.readlines()
	airports = [x.strip() for x in airports]

	return(airports)

def get_weather(airports):
	# Retrieve METAR from aviationweather.gov data server
	# Details about parameters can be found here: https://www.aviationweather.gov/dataserver/example?datatype=metar
	url = "https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&hoursBeforeNow=5&mostRecentForEachStation=true&stationString=" + ",".join([item for item in airports if item != "NULL"])
	logging.info ("Retriving from " + url)
	req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36 Edg/86.0.622.69'})
	content = urllib.request.urlopen(req).read()
	# Retrieve flying conditions from the service response and store in a dictionary for each airport
	root = ET.fromstring(content)
	conditionDict = { "NULL": {"flightCategory" : "", "windDir": "", "windSpeed" : 0, "windGustSpeed" :  0, "windGust" : False, "lightning": False, "tempC" : 0, "dewpointC" : 0, "vis" : 0, "altimHg" : 0, "obs" : "", "skyConditions" : {}, "obsTime" : datetime.datetime.now() } }
	conditionDict.pop("NULL")
	stationList = []
	for metar in root.iter('METAR'):
		stationId = metar.find('station_id').text
		if metar.find('flight_category') is None:
			print("Missing flight condition, skipping.")
			continue
		flightCategory = metar.find('flight_category').text
		windDir = ""
		windSpeed = 0
		windGustSpeed = 0
		windGust = False
		lightning = False
		tempC = 0
		dewpointC = 0
		vis = 0
		altimHg = 0.0
		obs = ""
		skyConditions = []
		if metar.find('wind_gust_kt') is not None:
			windGustSpeed = int(metar.find('wind_gust_kt').text)
			windGust = (True if (ALWAYS_BLINK_FOR_GUSTS or windGustSpeed > WIND_BLINK_THRESHOLD) else False)
		if metar.find('wind_speed_kt') is not None:
			windSpeed = int(metar.find('wind_speed_kt').text)
		if metar.find('wind_dir_degrees') is not None:
			windDir = metar.find('wind_dir_degrees').text
		if metar.find('temp_c') is not None:
			tempC = int(round(float(metar.find('temp_c').text)))
		if metar.find('dewpoint_c') is not None:
			dewpointC = int(round(float(metar.find('dewpoint_c').text)))
		if metar.find('visibility_statute_mi') is not None:
			vis = int(round(float(metar.find('visibility_statute_mi').text)))
		if metar.find('altim_in_hg') is not None:
			altimHg = float(round(float(metar.find('altim_in_hg').text), 2))
		if metar.find('wx_string') is not None:
			obs = metar.find('wx_string').text
		if metar.find('observation_time') is not None:
			obsTime = datetime.datetime.fromisoformat(metar.find('observation_time').text.replace("Z","+00:00"))
		for skyIter in metar.iter("sky_condition"):
			skyCond = { "cover" : skyIter.get("sky_cover"), "cloudBaseFt": int(skyIter.get("cloud_base_ft_agl", default=0)) }
			skyConditions.append(skyCond)
		if metar.find('raw_text') is not None:
			rawText = metar.find('raw_text').text
			lightning = False if rawText.find('LTG') == -1 else True
		logging.info(stationId + ":" 
		+ flightCategory + ":" 
		+ str(windDir) + "@" + str(windSpeed) + ("G" + str(windGustSpeed) if windGust else "") + ":"
		+ str(vis) + "SM:"
		+ obs + ":"
		+ str(tempC) + "/"
		+ str(dewpointC) + ":"
		+ str(altimHg) + ":"
		+ str(lightning))
		conditionDict[stationId] = { "flightCategory" : flightCategory, "windDir": windDir, "windSpeed" : windSpeed, "windGustSpeed": windGustSpeed, "windGust": windGust, "vis": vis, "obs" : obs, "tempC" : tempC, "dewpointC" : dewpointC, "altimHg" : altimHg, "lightning": lightning, "skyConditions" : skyConditions, "obsTime": obsTime }
		stationList.append(stationId)
	return(conditionDict)


def calc_target_colors (stations, conditions):  # calculate an array of bulb states given the list of stations and dict of conditions.  Returns an array of (color, blink) values
	target_colors = []
	for airportcode in stations:
		windy = False
		lightningConditions = False
		color = COLOR_CLEAR
		# Skip NULL entries
		if airportcode != "":
			condition = conditions.get(airportcode, None)

			if condition != None:
				windy = True if (ACTIVATE_WINDCONDITION_ANIMATION and (condition["windSpeed"] > WIND_BLINK_THRESHOLD or condition["windGust"] == True)) else False

				if condition["lightning"]:
					color = COLOR_LIGHTNING
				elif condition["flightCategory"] == "VFR":
					color = COLOR_VFR
				elif condition["flightCategory"] == "MVFR":
					color = COLOR_MVFR
				elif condition["flightCategory"] == "IFR":
					color = COLOR_IFR
				elif condition["flightCategory"] == "LIFR":
					color = COLOR_LIFR
				else:
					color = COLOR_CLEAR

				logging.debug ("Setting LED for " + airportcode + " to " + ("lightning " if lightningConditions else "") + ("windy " if windy else "") + (condition["flightCategory"] if conditions != None else "None") + " " + str(color))

		target_colors.append((color,windy))

	return(target_colors)



# ---------------------------------------------------------------------------
# ------------START OF MAIN FLOW---------------------------------------------
# ---------------------------------------------------------------------------

initialize_logging()

logging.info ("Running metar.py at %s", datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))

calc_daytime()



# ---------------------------------------------------------------------------
# ------------START OF MAIN DISPLAY LOOP-------------------------------------
# ---------------------------------------------------------------------------


while True:
	pixels,disp = initialize_display_and_leds()
	airports = get_airport_list()
	conditionDict = get_weather(airports)
	ledstate = calc_target_colors(airports,conditionDict)

	num_display_loops = int(REFRESH_TIME_SECONDS/(DISPLAY_ROTATION_SPEED*len(airports)))
	threadarray=[]

	for p in range(len(ledstate)):
		pixels[p],b = ledstate[p]
		# Update actual LEDs all at once

	# for windy stations, spin up a blinky thread per station and store a pointer to each thread in threadarray
	for p in range(len(ledstate)):
		if ledstate[p][1]:
			logging.debug("blinking station %s", str(p))

			x = threading.Thread(target=blinkme, args=(p,ledstate[p][0],9999,BLINK_SPEED))  # very long blink period - assume the thread will get killed
			x.start()
			threadarray.append(x)
		else:
			threadarray.append('')

	pixels.show()

	if disp is not None:	# Rotate through airports METAR on external display until it's time to refresh the weather

		for l in range(num_display_loops):
			logging.debug("Starting loop %s of %s",str(l),str(num_display_loops))

			p = 0
			for metarStation in airports:
# if this station is blinking, and we are fastblinking, kill that thread
				if FAST_BLINK_DISPLAYED_STATION and ledstate[p][1]:
					STOPFLAG = p
					threadarray[p].join()  #pauses until the thread is dead
					STOPFLAG = DONTSTOP

				if metarStation != "NULL" and conditionDict.get(metarStation):
					logging.debug("Showing METAR Display for %s %s", str(p) , metarStation)
					displaymetar.outputMetar(disp, metarStation, conditionDict.get(metarStation))
					if FAST_BLINK_DISPLAYED_STATION:
						thiscolor, b  = ledstate[p]
						blinkme (p, thiscolor, DISPLAY_ROTATION_SPEED, FAST_BLINK_SPEED)
					# reset the pixel
						pixels[p],b =ledstate[p]
# restart the blinking thread if needed
						if ledstate[p][1]:
							threadarray[p] = threading.Thread(target=blinkme, args=(p,ledstate[p][0],9999,BLINK_SPEED))  # very long blink period - assume the thread will get killed
							threadarray[p].start()
						pixels.show()
					else:
						sleep(DISPLAY_ROTATION_SPEED)
				p += 1

		logging.info ('...kill all the threads...')
# kill all the windy loops bafore refreshing
		for p in range(len(ledstate)):
			if ledstate[p][1]:
				STOPFLAG = p
				threadarray[p].join()
				STOPFLAG = DONTSTOP

	else:
		sleep(REFRESH_TIME_SECONDS)   #If there's no display, then just pause for the refresh time
	logging.info ('ready to refresh the weather')
