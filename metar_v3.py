import requests
import time
import re
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

# =============================
# TELEGRAM CONFIG
# =============================

TOKEN = "8705089258:AAHIeqsrgQhv1-rzHr9zamgvTYsSXW0BgoA"
CHAT_ID = "8554750866"

def send_telegram(msg):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }

    requests.post(url,data=data)


# =============================
# METAR SOURCE 1
# AviationWeather
# =============================

def get_metar_aviationweather():

    url = "https://aviationweather.gov/api/data/metar?ids=VTUL&format=raw"

    try:

        r = requests.get(url,timeout=30)

        if r.status_code == 200:

            return r.text.strip()

    except:
        pass

    return None


# =============================
# NOAA FALLBACK
# =============================

def get_metar_noaa():

    url = "https://tgftp.nws.noaa.gov/data/observations/metar/stations/VTUL.TXT"

    try:

        r = requests.get(url)

        if r.status_code == 200:

            lines = r.text.split("\n")

            return lines[-1]

    except:
        pass

    return None


# =============================
# CHECK SPECI TMD
# =============================

def check_speci():

    url="http://metcom.tmd.go.th:20080/Record_data/Metar_free_form_list"

    try:

        r=requests.get(url)

        soup=BeautifulSoup(r.text,"html.parser")

        text=soup.get_text()

        if "SPECI VTUL" in text:

            return True

    except:
        pass

    return False


# =============================
# METAR PARSER
# =============================

def parse_metar(metar):

    data = {}

    data["metar"] = metar

    vis = re.search(r"\s(\d{4})\s",metar)

    if vis:
        data["visibility"] = int(vis.group(1))
    else:
        data["visibility"] = 9999


    wind = re.search(r"(\d{3})(\d{2})KT",metar)

    if wind:

        data["wind_dir"] = int(wind.group(1))
        data["wind_speed"] = int(wind.group(2))

    else:

        data["wind_speed"] = 0


    if "TS" in metar:
        data["ts"] = True
    else:
        data["ts"] = False


    if "FG" in metar:
        data["fog"] = True
    else:
        data["fog"] = False


    if "BR" in metar:
        data["mist"] = True
    else:
        data["mist"] = False


    return data


# =============================
# RISK MODEL
# =============================

def risk_model(data):

    risk = "LOW"

    if data["ts"]:
        risk="HIGH"

    if data["fog"]:
        risk="HIGH"

    if data["visibility"] <= 1000:
        risk="HIGH"

    elif data["visibility"] < 2000:
        risk="MEDIUM"

    if data["wind_speed"] >= 20:
        risk="HIGH"

    elif data["wind_speed"] >= 15:
        risk="MEDIUM"

    return risk


# =============================
# SAVE HISTORY
# =============================

def save_history(data,risk):

    row={

        "time":datetime.utcnow(),

        "metar":data["metar"],

        "visibility":data["visibility"],

        "wind":data["wind_speed"],

        "risk":risk

    }

    df=pd.DataFrame([row])

    try:

        old=pd.read_csv("metar_history.csv")

        df=pd.concat([old,df])

    except:
        pass

    df.to_csv("metar_history.csv",index=False)


# =============================
# DUPLICATE CHECK
# =============================

def is_new_metar(metar):

    try:

        with open("last_metar.txt","r") as f:

            last=f.read()

    except:

        last=""

    if metar!=last:

        with open("last_metar.txt","w") as f:

            f.write(metar)

        return True

    return False


# =============================
# MAIN LOOP
# =============================

def main():

    send_telegram("VTUL METAR Monitoring System Started")

    while True:

        metar=get_metar_aviationweather()

        if not metar:

            metar=get_metar_noaa()

        if metar:

            if is_new_metar(metar):

                data=parse_metar(metar)

                risk=risk_model(data)

                save_history(data,risk)

                msg=f"""
VTUL METAR UPDATE

{metar}

Visibility : {data['visibility']} m
Wind : {data['wind_speed']} kt
Risk : {risk}
"""

                if risk!="LOW":

                    send_telegram(msg)

                else:

                    send_telegram("METAR Updated (System OK)")

        if check_speci():

            send_telegram("SPECI DETECTED VTUL")

        time.sleep(300)


if __name__=="__main__":

    main()
