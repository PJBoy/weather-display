# Example metar file: http://weather.noaa.gov/pub/data/observations/metar/cycles/00Z.TXT
# Decoding documentation: http://atmo.tamu.edu/class/metar/quick-metar.html
# Example location webpage: http://weather.gladstonefamily.net/site/search?site=UKOO


import pymysql
import re
import urllib.request

def UpdateDatabase():       # Insert the database update vector to the Metar table in the MySQL database
    global DatabaseData
    KeyBuffer = [x[0]+',' for x in DatabaseData]	# Collect the keys
    ValueBuffer = [x[1]+"'," for x in DatabaseData]	# Collect the values
    print("REPLACE `Metar`(" + ''.join(KeyBuffer)[:-1] + ") VALUES(" + ''.join(ValueBuffer)[:-1] + ");")    # Debug function
    Database.execute("REPLACE `Metar`(" + ''.join(KeyBuffer)[:-1] + ") VALUES(" + ''.join(ValueBuffer)[:-1] + ");")
    DatabaseData = []       # Initialise the next set of data
    return

def DatabaseDataAdd(key, item): # Add to the database update vector.  Escapes apostrophes, and surrounds in quotes
    global DatabaseData
    DatabaseData += [[key, "'"+str(item).replace("'", "''")]]
    return

def Decode_date(CurrentCharacter):  # 0 "yyyy/mm/dd "
    global CurrentLine              # Requires no parsing; always exists
    print("date\n" + CurrentLine[CurrentCharacter:])    # Debug function
    DatabaseDataAdd("`date`", CurrentLine[CurrentCharacter:CurrentCharacter+10])    # Send the 10-character date
    return 1, CurrentCharacter+11   # Size of data + 1

def Decode_time(CurrentCharacter):  # 1 "hh:mm\n"
    global CurrentLine              # Append :00; always exists
    print("time\n" + CurrentLine[CurrentCharacter:])    # Debug function
    DatabaseDataAdd("`time`", CurrentLine[CurrentCharacter:CurrentCharacter+5]+":00")   # Send the 8-character time
    return None, CurrentCharacter+6 # Size of data + 1

def Decode_location(CurrentCharacter):  # 0 "XXXX "
                                        # short_location: Requires no parsing; always exists
    global CurrentLine                  # Also handles location, latitude and longitude; reads from the HTML of a website that takes the four character code as a URL parameter
    print("location\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = CurrentLine[CurrentCharacter:CurrentCharacter+4]
    DatabaseDataAdd("`short_location`", element)                # Send the 4-character short_location
    Webpage = urllib.request.urlopen("http://weather.gladstonefamily.net/site/search?site=" + element)  # Find the relevant webpage
    WebpageContent = str(Webpage.read(8192))        # Load the first 8k
    LocationInfo = WebpageContent.find("Latitude")  # Start of the locational data section
    if LocationInfo != -1 and WebpageContent[LocationInfo:LocationInfo+34] != "Latitude and Longitude are unknown": # If location is known:
        Location = WebpageContent.find("Location", LocationInfo)                                       #\
        DatabaseDataAdd("`location`", WebpageContent[Location+10:WebpageContent.find('<', Location)])  #} Location
        Latitude = WebpageContent.find(',', LocationInfo)+2                                            #\
        DatabaseDataAdd("`latitude`", WebpageContent[Latitude:WebpageContent.find('&', Latitude)])     #} Latitude
        Longitude = WebpageContent.find(',', WebpageContent.find("Longitude", LocationInfo))+2         #\
        DatabaseDataAdd("`longitude`", WebpageContent[Longitude:WebpageContent.find('&', Longitude)])  #} Longitude
    return 1, CurrentCharacter+5    # Size of data + 1

def Decode_datetime_skip(CurrentCharacter): # 1 "ddhhmmZ "
    global CurrentLine                      # Skip function; fixed length; always exists
    print("datetime_skip\n" + CurrentLine[CurrentCharacter:])    # Debug function
    return 2, CurrentCharacter+8    # Size of data + 1

def Decode_report_modifier_skip(CurrentCharacter):  # 2 "[AUTO] " / "[COR] "
    global CurrentLine                              # Skip function; presence check, predefined possible values
    print("report_modifier_skip\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = CurrentLine[CurrentCharacter:CurrentLine.find(' ', CurrentCharacter)] # Between word boundaries
    if element == "AUTO ":
        offset = 5
    elif element == "COR ":
        offset = 4
    else:
        offset = 0
    return 3, CurrentCharacter+offset   # Size of data+1 if any

def Decode_wind_bearing(CurrentCharacter):  # 3 "VRB" / "bbb"
    global CurrentLine                      # Presence check, ignore VRB, needs no parsing
    print("wind_bearing\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = CurrentLine[CurrentCharacter:CurrentCharacter+3]
    if re.compile(r'\d\d\d').match(element):        # If three digits:
        DatabaseDataAdd("`wind_bearing`", element)  # Send the bearing
    elif element != "VRB":          # If not VRB, then not wind_bearing data
        return 4, CurrentCharacter  # Return current character
    return 4, CurrentCharacter+3

def Decode_wind_knots(CurrentCharacter):    # 4 "kk[k]G" / "kk[k]KT " / "kk[k]MPS "
    global CurrentLine                      # Can change program flow, MPS needs unit conversion, variable length, presence check
    print("wind_knots\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = re.compile(r'(\d{2,3})(G|KT |MPS )').match(CurrentLine[CurrentCharacter:])    # Get the value and the suffix
    if not element:                 # Not wind_knots data
        return 6, CurrentCharacter  # Return current character
    if element.group(2) == 'G':     # Suffix G
        item = element.group(1)     # No unit conversion
        decodeOffset = 5            # Decode gust data
    elif element.group(2) == "KT ": # Suffix KT
        item = element.group(1)     # No unit conversion
        decodeOffset = 6            # Skip gust decoding
    else:                                                   # Suffix MPS
        item = round(int(element.group(1)) * 1.94384449)    # Unit conversion
        decodeOffset = 6                                    # Skip gust decoding
    DatabaseDataAdd("`wind_knots`", item)   # Send data
    return decodeOffset, CurrentCharacter+len(element.group(0)) # Size of captured data

def Decode_wind_gust_knots(CurrentCharacter):   # 5 "gg[g]KT " / "gg[g]MPS "
    global CurrentLine                          # Variable length, MPS needs unit conversion, always exists (conditionally executed)
    print("wind_gust_knots\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = re.compile(r'(\d{2,3})(KT|MPS) ').match(CurrentLine[CurrentCharacter:])   # Get the value and the suffix
    if element.group(2) == "KT":    # Suffix KT
        item = element.group(1)     # No unit conversion
    else:                                                   # Suffix MPS
        item = round(int(element.group(1)) * 1.94384449)    # Unit conversion
    DatabaseDataAdd("`wind_gust_knots`", item)              # Send data
    return 6, CurrentCharacter+len(element.group(0))        # Size of captured data

def Decode_wind_bearing_range(CurrentCharacter):    # 6 "mmmVxxx "
    global CurrentLine                              # Presence check, difference is calculated, V is ignored
    print("wind_bearing_range\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = re.compile(r'(\d\d\d)V(\d\d\d) ').match(CurrentLine[CurrentCharacter:])   # Get limits
    if not element:                 # Not wind_bearing_range data
        return 7, CurrentCharacter  # Return current character
    DatabaseDataAdd("`wind_bearing_range`", abs(int(element.group(2)) - int(element.group(1)))) # Send difference
    return 7, CurrentCharacter+8    # Size of data + 1

def Decode_visibility(CurrentCharacter):    # 7 "M1/4SM " / "n/dSM " / "q[q][ n/d]SM " / "qqqq " / "CAVOK "
    global CurrentLine                      # Variable format, variable lengths, unit conversion for metres, can change program flow
    print("visibility\n" + CurrentLine[CurrentCharacter:])    # Debug function
    if CurrentLine[CurrentCharacter:CurrentCharacter+6] == "CAVOK ":    # CAV OK
        item = 9999         # Greatest visibility
        offset = 6          # Size of data + 1
        decodeOffset = 20   # Skip all decoding until temperature
    if CurrentLine[CurrentCharacter:CurrentCharacter+7] == 'M1/4SM ':
        item = 0.24         # Less than 1/4
        offset = 7          # Size of data + 1
        decodeOffset = 8    # Nothing skipped
    else:
        element = re.compile(r'(\d\d\d\d) ').match(CurrentLine[CurrentCharacter:])  # Try and get qqqq
        if element:     # If qqqq
            item = int(element.group(1)) * 0.000539956803    # Unit conversion from metres
            offset = 5  # Size of data + 1
        else:
            element = re.compile(r'(\d)/(\d)SM ').match(CurrentLine[CurrentCharacter:])  # Try and get n and d without q
            if element:     # If n/d
                item = int(element.group(2)) / int(element.group(1))    # Send n/d
                offset = 6  # Size of data + 1
            else:
                element = re.compile(r'(\d{1,2})(?: (\d)/(\d))?SM ').match(CurrentLine[CurrentCharacter:])  # Try and get q, n and d
                if not element: # If not visibility data
                    return 8, CurrentCharacter      # Return current character
                if not element.group(2):            # If no n/d:
                    item = int(element.group(1))    # Send q
                else:       # If n/d
                    item = int(element.group(1))  +  int(element.group(2)) / int(element.group(3))  # Send q + n/d
                offset = len(element.group(0))  # Size of captured data
        decodeOffset = 8    # Nothing skipped
    DatabaseDataAdd("`visibility`", item)       # Send data
    return decodeOffset, CurrentCharacter+offset

def Decode_rvr_runway_skip(CurrentCharacter):   # 8 "Rrr[L|C|R]/"
    global CurrentLine                          # Skip function, presence check, variable length, can change program flow
    print("rvr_runway_skip\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = re.compile(r'R\d\d[LCR]?/').match(CurrentLine[CurrentCharacter:]) # Capture any runway data
    if not element: # If not runway data
        return 11, CurrentCharacter # Skip rvr_visual_range decoding at current character
    return 9, CurrentCharacter+len(element.group(0))    # Size of captured data

def Decode_rvr_visual_range_min_skip(CurrentCharacter): # 9 "nnnnV" / "nnnnFT " / "M0600FT[/U|D] " / "P6000FT[/U|D] "
    global CurrentLine                                  # Skip function, variable format, can change program flow, variable lengths, presence check
    print("rvr_visual_range_min_skip\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = re.compile(r'(?:M0600|P6000)FT(?:/[DU])? ').match(CurrentLine[CurrentCharacter:]) # Capture third and fourth formats
    if not element:
        element = re.compile(r'\d\d\d\d(?:(V)|FT )').match(CurrentLine[CurrentCharacter:])      # Capture first and second formats
        if not element:         # If not rvr_visual_range data
            offset = 0          # Return same character
            decodeOffset = 11   # Skip rvr_visual_range_max decoding
        elif element.group(1):  # If V
            offset = 5          # Size of data
            decodeOffset = 10   # Nothing skipped
        else:                   # FT
            offset = 7          # Size of data + 1
            decodeOffset = 11   # Skip rvr_visual_range_max decoding
    else:                       # Third or fourth format
        offset = len(element.group(0))  # Size of captured data
        decodeOffset = 11       # Skip rvr_visual_range_max decoding
    return 10, CurrentCharacter+offset

def Decode_rvr_visual_range_max_skip(CurrentCharacter): # 10 "nnnnFT " / "P60000FT[/U|D] "
    global CurrentLine                                  # Skip function, fixed length, always exists (conditionally executed)
    print("rvr_visual_range_max_skip\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = re.compile(r'P6000FT(?:/[DU])? ').match(CurrentLine[CurrentCharacter:])  # Capture second format
    if element:
        offset = len(element.group(0))
    else:   # First format
        offset = 7
    return 11, offset   # Size of data + 1

                        # Though only one set of weather data is recorded, there can be any number of weather data sets in the report
                        # All sets need to be parsed, but only the first recorded
weather = False         # Weather decoding functions will be repeated until weather is not true, weather is set to true each time a valid weather format is encountered

weather_intensity = 1   # Used for ensuring only the first weather intensity is added

def Decode_weather_intensity(CurrentCharacter): # 11 "[+]" / "[-]"
    global CurrentLine                          # Presence check, fixed length, predefined possible values, multiple possible entries (only taking first)
    print("weather_intensity\n" + CurrentLine[CurrentCharacter:])    # Debug function
    global weather_intensity, weather
    weather = False
    if CurrentLine[CurrentCharacter] == '+':    #\ 
        item = "Heavy"                          #} Heavy
        offset = 1      # Size of data
        weather = True  # Processed weather
    elif CurrentLine[CurrentCharacter] == '-':  #\
        item = "Light"                          #} Light
        offset = 1      # Size of data
        weather = True  # Processed weather
    else:
        offset = 0      # No data
    if CurrentLine[CurrentCharacter+offset:CurrentCharacter+offset+2] == "VC":  # Ignoring
        offset += 4
    if weather_intensity <= 1 and weather:              # If not already added weather_intensity
        DatabaseDataAdd("`weather_intensity`", item)    # Send data
        weather_intensity += 1                          # Added weather_intensity
    return 12, CurrentCharacter+offset

weather_descriptor = 1  # Used for ensuring only the first weather descriptor is added

def Decode_weather_descriptor(CurrentCharacter):    # 12 "[DD]"
    global CurrentLine                              # Presence check, fixed length, predefined possible values, can change program flow, multiple possible entries (only taking first)
    print("weather_descriptor\n" + CurrentLine[CurrentCharacter:])    # Debug function
    global weather_descriptor, weather
    if CurrentLine[CurrentCharacter] == ' ':    # End of current weather data set
        if weather:                             #\
            return 11, CurrentCharacter+1       #} Try next set if current set processed
        return 16, CurrentCharacter+1           # Else skip the rest of the weather functions
    weatherDescriptors = {"MI": "Shallow", "PR": "Partial", "BC": "Patches", "DR": "Low Drifting", "BL": "Blowing", "SH": "Shower", "TS": "Thunderstorm", "FZ": "Freezing"}
    if CurrentLine[CurrentCharacter:CurrentCharacter+2] in weatherDescriptors:  # If a descriptor
        if weather_descriptor <= 1: # If not already added weather_descriptor
            DatabaseDataAdd("`weather_descriptor`", weatherDescriptors[CurrentLine[CurrentCharacter:CurrentCharacter+2]])   # Send descriptor
            weather_descriptor += 1 # Added weather_descriptor
        weather = True  # Processed weather
        offset = 2  # Size of data
    else:
        offset = 0  # No data
    return 13, CurrentCharacter+offset

weather_precipitation = 1  # Used for ensuring only the first weather precipitation is added

def Decode_weather_precipitation(CurrentCharacter): # 13 "[PP]"
    global CurrentLine                              # Presence check, fixed length, predefined possible values, can change program flow, multiple possible entries (only taking first)
    print("weather_precipitation\n" + CurrentLine[CurrentCharacter:])    # Debug function
    global weather_precipitation, weather
    if CurrentLine[CurrentCharacter] == ' ':    # End of current weather data set
        if weather:                             #\
            return 11, CurrentCharacter+1       #} Try next set if current set processed
        return 16, CurrentCharacter+1           # Else skip the rest of the weather functions
    weatherPrecipitations = {"DZ": "Drizzle", "RA": "Rain", "SN": "Snow", "SG": "Snow Grains", "IC": "Ice Crystals", "PL": "Ice Pellets", "GR": "Hail", "GS": "Small Hail", "UP": "Unknown"}
    if CurrentLine[CurrentCharacter:CurrentCharacter+2] in weatherPrecipitations:   # If a precipitation
        if weather_precipitation <= 1:  # If not already added weather_precipitation
            DatabaseDataAdd("`weather_precipitation`", weatherPrecipitations[CurrentLine[CurrentCharacter:CurrentCharacter+2]]) # Send precipitation
            weather_precipitation += 1  # Added weather_precipitation
        weather = True  # Processed weather
        offset = 2  # Size of data
    else:         
        offset = 0  # No data
    return 14, CurrentCharacter+offset

weather_obscuration = 1  # Used for ensuring only the first weather obscuration is added

def Decode_weather_obscuration(CurrentCharacter):   # 14 "[OO]"
    global CurrentLine                              # Presence check, fixed length, predefined possible values, can change program flow, multiple possible entries (only taking first)
    print("weather_obscuration\n" + CurrentLine[CurrentCharacter:])    # Debug function
    global weather_obscuration, weather
    if CurrentLine[CurrentCharacter] == ' ':    # End of current weather data set
        if weather:                             #\
            return 11, CurrentCharacter+1       #} Try next set if current set processed
        return 16, CurrentCharacter+1           # Else skip the rest of the weather functions
    weatherObscurations = {"BR": "Mist", "FG": "Fog", "FU": "Smoke", "VA": "Volcanic Ash", "DU": "Widespread Dust", "SA": "Sand", "HZ": "Haze", "PY": "Spray"}
    if CurrentLine[CurrentCharacter:CurrentCharacter+2] in weatherObscurations: # If an obscuration
        if weather_obscuration <= 1:    # If not already added weather_obscuration
            DatabaseDataAdd("`weather_obscuration`", weatherObscurations[CurrentLine[CurrentCharacter:CurrentCharacter+2]]) # Send obscuration
            weather_obscuration += 1    # Added weather_obscuration
        weather = True  # Processed weather
        offset = 2  # Size of data
    else:         
        offset = 0  # No data
    return 15, CurrentCharacter+offset

weather_other = 1  # Used for ensuring only the first weather other is added

def Decode_weather_other(CurrentCharacter): # 15 "[OO]"
    global CurrentLine                      # Presence check, fixed length, predefined possible values, can change program flow, multiple possible entries (only taking first)
    print("weather_other\n" + CurrentLine[CurrentCharacter:])    # Debug function
    global weather_other, weather
    if CurrentLine[CurrentCharacter] == ' ':    # End of current weather data set
        if weather:                             #\
            return 11, CurrentCharacter+1       #} Try next set if current set processed
        return 16, CurrentCharacter+1           # Else skip the rest of the weather functions
    weatherOthers = {"PO": "Sand Whirls", "SQ": "Squalls", "FC": "Funnel Cloud", "SS": "Sandstorm", "DS": "Duststorm"}
    if CurrentLine[CurrentCharacter:CurrentCharacter+2] in weatherOthers:   # If an other
        if weather_other <= 1:  # If not already added weather_other
            DatabaseDataAdd("`weather_other`", weatherOthers[CurrentLine[CurrentCharacter:CurrentCharacter+2]]) # Send other
            weather_other += 1  # Added weather_other
        weather = True  # Processed weather
    if weather:                     # If processed weather
        return 11, CurrentCharacter # Try next set of weather data
    return 16, CurrentCharacter


sky = 0  # Used for ensuring only the first three sky reports are added, also the database column variable

def Decode_sky_condition(CurrentCharacter): # 16 "CCC" / "VV"
    global CurrentLine                      # Presence check, variable format, fixed length, can change program flow
    print("sky_condition\n" + CurrentLine[CurrentCharacter:])    # Debug function
    global sky
    global weather_intensity, weather_descriptor, weather_precipitation, weather_obscuration, weather_other, weather  #\
    weather_intensity = weather_descriptor = weather_precipitation = weather_obscuration = weather_other = 1          #} Resets weather variable
    weather = False                                                                                                   #/
    sky += 1    # Next sky data set
    
    if '/' in CurrentLine[CurrentCharacter+2:CurrentCharacter+4]:   # If temperature
        sky = 0 # Reset sky data sets processed
        return 20, CurrentCharacter # Skip to temperature decoding
    if sky > 3: # If done all three sets
        return 16, CurrentLine.find(' ', CurrentCharacter) + 1  # Find word boundary and skip to temperature decoding
    if CurrentLine[CurrentCharacter] == 'V':    # Vertical visibility
        return 18, CurrentCharacter+2           # Decode sky_vertical_visibility
    skyConditions = {"CLR": "Clear", "SKC": "Clear", "NCD": "Clear", "FEW": "Few", "SCT": "Scattered", "BKN": "Broken", "OVC": "Overcast"}
    element = CurrentLine[CurrentCharacter:CurrentCharacter+3]
    if element in skyConditions:                # If a condition
        DatabaseDataAdd("`sky_condition_" + str(sky) + '`', skyConditions[element]) # Send condition
        if element in ("CLR", "SKC", "NCD"):    # If clear sky
            return 20, CurrentCharacter+4       # No other sky data, skip to temperature decoding
        return 17, CurrentCharacter+3           # Else, decode sky_height
    return 20, CurrentCharacter                 # Not sky data, skip to temperature decoding

def Decode_sky_height(CurrentCharacter):    # 17 "hhh"
    global CurrentLine                      # Fixed length, always exists (conditionally executed)
    print("sky_height\n" + CurrentLine[CurrentCharacter:])    # Debug function
    global sky
    DatabaseDataAdd("`sky_height_" + str(sky) + '`', CurrentLine[CurrentCharacter:CurrentCharacter+3])  # Send height
    return 19, CurrentCharacter+3   # Size of data, skip to sky_other decoding

def Decode_sky_vertical_visibility(CurrentCharacter):   # 18 "vvv"
    global CurrentLine                                  # Fixed length, always exists (conditionally executed)
    print("sky_vertical_visibility\n" + CurrentLine[CurrentCharacter:])    # Debug function
    global sky
    DatabaseDataAdd("`sky_vertical_visibility_" + str(sky) + '`', CurrentLine[CurrentCharacter:CurrentCharacter+3]) # Send vertical visibility
    return 19, CurrentCharacter+3   # Size of data

def Decode_sky_other(CurrentCharacter): # 19 "CB " / "TCU " / "/// "
    global CurrentLine                  # Presence check, predefined possible values
    print("sky_other\n" + CurrentLine[CurrentCharacter:])    # Debug function
    global sky
    if CurrentLine[CurrentCharacter] == ' ':    # If not other
        return 16, CurrentCharacter+1           # Try next sky data set
    if CurrentLine[CurrentCharacter:CurrentCharacter+4] == '/// ':  # If third format
        return 16, CurrentCharacter+4   # Try next sky data set, ignore
    skyOthers = {"CB": "Cumulonimbus", "TCU": "Towering Cumulus"}
    element = CurrentLine[CurrentCharacter:CurrentLine.find(' ', CurrentCharacter)] # Until word boundary
    DatabaseDataAdd("`sky_other_" + str(sky) + '`', skyOthers[element]) # Send element
    return 16, CurrentCharacter+len(element)+1  # Try next sky data set, size of data + 1

def Decode_temperature(CurrentCharacter):   # 20 "[M]tt/"
    global CurrentLine                      # Variable length, always exists, replace 'M' with '-'
    print("temperature\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = re.compile(r'(M)?(\d\d)/').match(CurrentLine[CurrentCharacter:])  # Capture any temperature data
    if not element: # If no temperature data
        offset = 0  # Current character
    else:
        if element.group(1):    # If M
            item = '-'          # Insert negative sign
            offset = 4          # Size of data
        else:                   # Else
            item = ''           # No negative sign
            offset = 3          # Size of data
        DatabaseDataAdd("`temperature`", item + element.group(2))   # Send temperature
    return 21, CurrentCharacter+offset

def Decode_dew_point(CurrentCharacter): # 21 "[M]dd "
    global CurrentLine                  # Variable length, always exists, replace 'M' with '-'
    print("dew_point\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = re.compile(r'(M)?(\d\d)').match(CurrentLine[CurrentCharacter:])   # Capture any dew pointer data
    if not element: # If no dew point data
        offset = 0  # Current character
    else:
        if element.group(1):    # If M
            item = '-'          # Insert negative sign
            offset = 4          # Size of data
        else:                   # Else
            item = ''           # No negative sign
            offset = 3          # Size of data
        DatabaseDataAdd("`dew_point`", item + element.group(2)) # Send dew point
    return 22, CurrentCharacter+offset

def Decode_pressure(CurrentCharacter):  # 22 "Aqqdd " / "Qpppp "
    global CurrentLine                  # Fixed length, presence check, A needs unit conversion
    print("pressure\n" + CurrentLine[CurrentCharacter:])    # Debug function
    element = re.compile(r'(A|Q)(\d\d\d\d)').match(CurrentLine[CurrentCharacter:])  # Get the value and the prefix
    if element:
        item = int(element.group(2))        # The value
        if element.group(1) == 'A':         # If inches of mercury
            item *= 0.3386                  # Unit conversion
        offset = 6                          # Size of data + 1
        DatabaseDataAdd("`pressure`", item) # Add pressure
    else:           # If not pressure
        offset = 0  # Current character
    return 23, CurrentCharacter+offset

def Decode_recent_skip(CurrentCharacter): # 23 "RExx[xx]"
    return None, None                     # Ignored, needs no parsing

# Decode functions for each element of the encoded file
Decode0 = [Decode_date, Decode_time]
Decode1 = [Decode_location, Decode_datetime_skip, Decode_report_modifier_skip, Decode_wind_bearing, Decode_wind_knots, Decode_wind_gust_knots, Decode_wind_bearing_range, Decode_visibility, Decode_rvr_runway_skip, Decode_rvr_visual_range_min_skip, Decode_rvr_visual_range_max_skip, Decode_weather_intensity, Decode_weather_descriptor, Decode_weather_precipitation, Decode_weather_obscuration, Decode_weather_other, Decode_sky_condition, Decode_sky_height, Decode_sky_vertical_visibility, Decode_sky_other, Decode_temperature, Decode_dew_point, Decode_pressure, Decode_recent_skip]
DecodeFunctions = [Decode0, Decode1]

# File to decode
MetarFile = urllib.request.urlopen("http://weather.noaa.gov/pub/data/observations/metar/cycles/00Z.TXT")
# Connection to weather database using localhost
DatabaseConnection = pymysql.connect(user="root", passwd="changing this before publicising", db="weather")
Database = DatabaseConnection.cursor()
# Create the table
#print("""
Database.execute("""
CREATE TABLE IF NOT EXISTS `Metar`
(
    `short_location`            char(4) key,
    `location`                  varchar(128),
    `longitude`                 float,
    `latitude`                  float,
    `date`                      date,
    `time`                      time,
    `wind_bearing`              int(3) unsigned zerofill,
    `wind_knots`                int,
    `wind_gust_knots`           int,
    `wind_bearing_range`        int(3) unsigned zerofill,
    `visibility`                float,
    `weather_intensity`         varchar(9),
    `weather_descriptor`        varchar(13),
    `weather_precipitation`     varchar(13),
    `weather_obscuration`       varchar(16),
    `weather_other`             varchar(13),
    `sky_condition_1`           varchar(10),
    `sky_height_1`              int,
    `sky_vertical_visibility_1` int,
    `sky_other_1`               varchar(17),
    `sky_condition_2`           varchar(10),
    `sky_height_2`              int,
    `sky_vertical_visibility_2` int,
    `sky_other_2`               varchar(17),
    `sky_condition_3`           varchar(10),
    `sky_height_3`              int,
    `sky_vertical_visibility_3` int,
    `sky_other_3`               varchar(17),
    `temperature`               int,
    `dew_point`                 int,
    `pressure`                  float,
    key `latitude` (`latitude`),
    key `longitude` (`longitude`)
)
ENGINE = MyISAM
DEFAULT CHARSET = utf8;
""")

# Main function
DecodeFunction = 0      # Which set of funtions to decode the current line with
DatabaseData = []       # The key and value pairs to be inserted per row
while True:
    try:
        CurrentLine = str(MetarFile.readline(), "ASCII")    # Read in the line (Global variable)
    except: # If ASCII decoding failed, move on to next line
        if DecodeFunction == 1: # If can't decode short_location
            DatabaseData = []   # Then clear the SQL data for the next entry
            DecodeFunction = 0  # Reset the set of decode functions
        else:
            DecodeFunction += 1 # Next set of functions
        continue
    if not CurrentLine:         # End function on EOF
        break
    if CurrentLine[0] == '\n':  # Ignore blank lines
        continue
    DecodeColumn = 0            # The database column that's to be decoded
    CurrentCharacter = 0        # The point in the line to be decoded
    while DecodeColumn != None and CurrentCharacter < len(CurrentLine)-1:
        if CurrentLine[CurrentCharacter:CurrentLine.find(' ', CurrentCharacter)] in ("RMK", "NOSPECI"):   # Not processing the remarks, nor synap
            break
        try:
            DecodeColumn, CurrentCharacter = DecodeFunctions[DecodeFunction][DecodeColumn](CurrentCharacter)    # Decode each column for the line
        except:
            break               # If unable to decode any data, ignore the rest of the line
    if DecodeFunction == 1:     # Because the data is multi-line, this checks to see if it's the last line of each set of data
        UpdateDatabase()        # Write the data to the database for the processed set
        DecodeFunction = 0      # Reset the set of decode functions
    else:
        DecodeFunction += 1     # Next set of functions

#print("ALTER TABLE `Metar` ORDER BY `latitude`, `longitude`;")
Database.execute("ALTER TABLE `Metar` ORDER BY `latitude`, `longitude`;")

Database.close()
DatabaseConnection.close()