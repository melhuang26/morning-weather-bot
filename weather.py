import os
import requests
import smtplib
from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from icalendar import Calendar

# Retrieve secrets
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
CALENDAR_ICS_URL = os.environ.get("CALENDAR_ICS_URL")

# CHANGE 1: Define a list of cities instead of just one
CITIES = ["Taipei", "Chiang Mai", "London"] 
TIMEZONE = ZoneInfo("Asia/Taipei") # Adjust if your primary timezone differs

def get_calendar_events():
    if not CALENDAR_ICS_URL:
        return ["No calendar URL configured."]
    
    try:
        response = requests.get(CALENDAR_ICS_URL)
        if response.status_code != 200:
            return ["Could not fetch calendar events."]
        
        cal = Calendar.from_ical(response.content)
        today = datetime.now(TIMEZONE).date()
        todays_events = []

        for component in cal.walk():
            if component.name == "VEVENT":
                summary = component.get("summary")
                dtstart = component.get("dtstart")
                
                if dtstart:
                    start_dt = dtstart.dt
                    if isinstance(start_dt, datetime):
                        if start_dt.tzinfo is not None:
                            local_dt = start_dt.astimezone(TIMEZONE)
                        else:
                            local_dt = start_dt.replace(tzinfo=TIMEZONE)
                        
                        event_date = local_dt.date()
                        time_str = local_dt.strftime("%H:%M")
                    else:
                        event_date = start_dt
                        time_str = "All-day"
                    
                    if event_date == today:
                        todays_events.append(f"<b>{time_str}</b> — {summary}")

        if not todays_events:
            return ["No events scheduled for today! Enjoy your free time."]
        
        return todays_events
    except Exception as e:
        return [f"Calendar Error: Could not parse events ({str(e)})"]

def get_aqi_info(lat, lon):
    aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}"
    res = requests.get(aqi_url)
    if res.status_code == 200:
        data = res.json()
        aqi_level = data["list"][0]["main"]["aqi"]
        aqi_descriptions = {1: "Good 😊", 2: "Fair 🙂", 3: "Moderate 😐", 4: "Poor 😷", 5: "Very Poor 🚨"}
        return aqi_descriptions.get(aqi_level, "Unknown")
    return "N/A"

def get_clothing_and_umbrella_tips(periods):
    all_desc = " ".join([p["description"].lower() for p in periods.values() if p])
    max_temp = max([p["temp"] for p in periods.values() if p] or [20])
    min_temp = min([p["temp"] for p in periods.values() if p] or [20])
    
    rain_keywords = ["rain", "drizzle", "thunderstorm", "shower"]
    if any(keyword in all_desc for keyword in rain_keywords):
        umbrella_tip = "☔ <b>Umbrella Alert:</b> Rain expected at some point today—take an umbrella!"
    else:
        umbrella_tip = "☀️ <b>Umbrella Alert:</b> No rain expected—leave the umbrella at home."
        
    if min_temp < 18:
        clothing_tip = "🧥 <b>Clothing Tip:</b> Chilly parts of the day! Bring a jacket or warm layer."
    elif max_temp > 28:
        clothing_tip = "👕 <b>Clothing Tip:</b> Warm during the day! Wear light, breathable clothes."
    else:
        clothing_tip = "👕 <b>Clothing Tip:</b> Comfortable temperatures overall today."
        
    return umbrella_tip, clothing_tip

def get_city_weather(city_name):
    """Fetches and parses weather data for a single city."""
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city_name}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch weather data for {city_name}: {response.text}")
    
    data = response.json()
    today = datetime.now(TIMEZONE).date()
    
    city_info = data.get("city", {})
    coord = city_info.get("coord", {"lat": 25.0330, "lon": 121.5654})
    aqi_status = get_aqi_info(coord["lat"], coord["lon"])

    periods = {"Morning": None, "Afternoon": None, "Night": None}
    
    for item in data.get("list", []):
        dt_local = datetime.fromtimestamp(item["dt"], tz=ZoneInfo("UTC")).astimezone(TIMEZONE)
        
        if dt_local.date() == today:
            hour = dt_local.hour
            weather_info = {
                "temp": item["main"]["temp"],
                "feels_like": item["main"]["feels_like"],
                "description": item["weather"][0]["description"].capitalize(),
                "humidity": item["main"]["humidity"]
            }
            
            if 6 <= hour <= 11 and periods["Morning"] is None:
                periods["Morning"] = weather_info
            elif 12 <= hour <= 17 and periods["Afternoon"] is None:
                periods["Afternoon"] = weather_info
            elif 18 <= hour <= 23 and periods["Night"] is None:
                periods["Night"] = weather_info

    # Fallbacks if exact hour brackets aren't matched
    available_items = [item for item in data.get("list", []) if datetime.fromtimestamp(item["dt"], tz=ZoneInfo("UTC")).astimezone(TIMEZONE).date() == today]
    if not periods["Morning"] and available_items:
        periods["Morning"] = {"temp": available_items[0]["main"]["temp"], "description": available_items[0]["weather"][0]["description"].capitalize(), "humidity": available_items[0]["main"]["humidity"]}
    if not periods["Afternoon"] and len(available_items) > 3:
        mid_idx = len(available_items) // 2
        periods["Afternoon"] = {"temp": available_items[mid_idx]["main"]["temp"], "description": available_items[mid_idx]["weather"][0]["description"].capitalize(), "humidity": available_items[mid_idx]["main"]["humidity"]}
    if not periods["Night"] and len(available_items) > 6:
        periods["Night"] = {"temp": available_items[-1]["main"]["temp"], "description": available_items[-1]["weather"][0]["description"].capitalize(), "humidity": available_items[-1]["main"]["humidity"]}

    umbrella_tip, clothing_tip = get_clothing_and_umbrella_tips(periods)
    
    return {
        "city": city_name,
        "aqi_status": aqi_status,
        "periods": periods,
        "umbrella_tip": umbrella_tip,
        "clothing_tip": clothing_tip
    }

def send_email(weather_data_list, schedule_events):
    msg = EmailMessage()
    date_str = datetime.now(TIMEZONE).strftime("%A, %B %d, %Y")
    primary_city = weather_data_list[0]["city"] if weather_data_list else "Multiple Cities"
    
    msg["Subject"] = f"☀️ Morning Briefing & Schedule ({date_str})"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS

    msg.set_content("Good morning! Check your HTML email view for today's weather and schedule briefing.")

    # Build HTML sections dynamically for each city
    weather_cards_html = ""
    for data in weather_data_list:
        periods_html = ""
        for title, info in data['periods'].items():
            if info:
                periods_html += f"""
                <div style="flex: 1; background: #ffffff; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center; margin: 4px;">
                    <h4 style="margin: 0 0 6px 0; font-size: 13px; color: #4f46e5;">{title}</h4>
                    <p style="margin: 4px 0; font-size: 16px; font-weight: bold;">{info['temp']}°C</p>
                    <p style="margin: 4px 0; font-size: 11px; color: #64748b;">{info['description']}</p>
                    <p style="margin: 4px 0; font-size: 10px; color: #94a3b8;">Humidity: {info['humidity']}%</p>
                </div>
                """
        
        weather_cards_html += f"""
        <div class="card" style="margin-bottom: 20px;">
            <h2>📍 {data['city']} — Weather & AQI</h2>
            <p style="margin-bottom: 10px;"><b>Air Quality (AQI):</b> {data['aqi_status']}</p>
            <div style="display: flex; gap: 6px;">
                {periods_html}
            </div>
            <div style="margin-top: 12px; font-size: 13px; background: #fffbeb; padding: 10px; border-radius: 6px; border-left: 4px solid #f59e0b;">
                <p style="margin: 2px 0;">{data['umbrella_tip']}</p>
                <p style="margin: 2px 0;">{data['clothing_tip']}</p>
            </div>
        </div>
        """

    schedule_html_items = "".join([f"<li style='margin-bottom: 8px;'>{event}</li>" for event in schedule_events])
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f4f7; color: #333333; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            .header {{ background: linear-gradient(135deg, #4f46e5, #3b82f6); color: #ffffff; padding: 28px 24px; text-align: center; }}
            .content {{ padding: 24px; }}
            .card {{ background: #f8fafc; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 6px; }}
            .schedule-card {{ background: #f0fdf4; border-left: 4px solid #22c55e; padding: 16px; margin-bottom: 16px; border-radius: 6px; }}
            h2 {{ margin-top: 0; font-size: 15px; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; }}
            ul {{ margin: 0; padding-left: 20px; }}
            .footer {{ text-align: center; font-size: 12px; color: #94a3b8; padding: 16px; border-top: 1px solid #e2e8f0; background: #fafafa; }}
            p {{ margin: 6px 0; font-size: 14px; line-height: 1.5; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0; font-size: 24px; font-weight: 700;">☀️ Morning Briefing</h1>
                <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.9;">{date_str}</p>
            </div>
            <div class="content">
                {weather_cards_html}

                <div class="schedule-card">
                    <h2>📅 Today's Schedule</h2>
                    <ul style="margin: 8px 0 0 0; padding-left: 18px;">
                        {schedule_html_items}
                    </ul>
                </div>
            </div>
            <div class="footer">
                <p>Automated Daily Briefing Bot • Powered by GitHub Actions 🤖</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.add_alternative(html_content, subtype='html')

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
    print("Multi-city weather and schedule briefing email sent successfully!")

if __name__ == "__main__":
    weather_results = []
    for city in CITIES:
        try:
            weather_results.append(get_city_weather(city))
        except Exception as e:
            print(f"Error fetching data for {city}: {e}")
            
    calendar_events = get_calendar_events()
    if weather_results:
        send_email(weather_results, calendar_events)
    else:
        print("No weather data could be fetched for any city.")
