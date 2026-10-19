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

CITY = "Taipei"
TIMEZONE = ZoneInfo("Asia/Taipei")

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

def get_clothing_and_umbrella_tips(temp, description):
    rain_keywords = ["rain", "drizzle", "thunderstorm", "shower"]
    if any(keyword in description.lower() for keyword in rain_keywords):
        umbrella_tip = "☔ <b>Umbrella Alert:</b> Rain expected, don't forget to take an umbrella!"
    else:
        umbrella_tip = "☀️ <b>Umbrella Alert:</b> No rain expected—leave the umbrella at home."
        
    if temp < 18:
        clothing_tip = "🧥 <b>Clothing Tip:</b> Chilly today! Wear a heavy coat or warm sweater."
    elif 18 <= temp <= 25:
        clothing_tip = "👕 <b>Clothing Tip:</b> Moderate weather! A long-sleeve shirt or light layer is perfect."
    else:
        clothing_tip = "👕 <b>Clothing Tip:</b> Warm weather! Wear light, breathable clothes."
        
    return umbrella_tip, clothing_tip

def get_weather_data():
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch weather data: {response.text}")
    
    data = response.json()
    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    description = data["weather"][0]["description"]
    humidity = data["main"]["humidity"]
    
    lat = data["coord"]["lat"]
    lon = data["coord"]["lon"]
    aqi_status = get_aqi_info(lat, lon)
    umbrella_tip, clothing_tip = get_clothing_and_umbrella_tips(temp, description)
    schedule_events = get_calendar_events()
    
    date_str = datetime.now(TIMEZONE).strftime("%A, %B %d, %Y")
    
    return {
        "city": CITY,
        "date_str": date_str,
        "temp": temp,
        "feels_like": feels_like,
        "description": description.capitalize(),
        "humidity": humidity,
        "aqi_status": aqi_status,
        "umbrella_tip": umbrella_tip,
        "clothing_tip": clothing_tip,
        "schedule_events": schedule_events
    }

def send_email(data):
    msg = EmailMessage()
    msg["Subject"] = f"☀️ Morning Briefing & Schedule for {data['city']} ({data['date_str']})"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS

    # Plain text fallback version
    schedule_text = "\n".join([f"• {e.replace('<b>', '').replace('</b>', '')}" for e in data['schedule_events']])
    plain_text = (
        f"Good morning! Here is your daily briefing for {data['city']} ({data['date_str']}):\n\n"
        f"Temperature: {data['temp']}°C (Feels like: {data['feels_like']}°C)\n"
        f"Condition: {data['description']}\n"
        f"Humidity: {data['humidity']}%\n"
        f"Air Quality (AQI): {data['aqi_status']}\n\n"
        f"--- Daily Tips ---\n"
        f"- {data['umbrella_tip'].replace('<b>','').replace('</b>','')}\n"
        f"- {data['clothing_tip'].replace('<b>','').replace('</b>','')}\n\n"
        f"--- Schedule ---\n"
        f"{schedule_text}\n\n"
        f"Have a wonderful day!"
    )
    msg.set_content(plain_text)

    # Rich HTML version
    schedule_html_items = "".join([f"<li style='margin-bottom: 8px;'>{event}</li>" for event in data['schedule_events']])
    
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
            .card {{ background: #f8fafc; border-left: 4px solid #3b82f6; padding: 16px; margin-bottom: 16px; border-radius: 6px; }}
            .tips-card {{ background: #fffbeb; border-left: 4px solid #f59e0b; padding: 16px; margin-bottom: 16px; border-radius: 6px; }}
            .schedule-card {{ background: #f0fdf4; border-left: 4px solid #22c55e; padding: 16px; margin-bottom: 16px; border-radius: 6px; }}
            h2 {{ margin-top: 0; font-size: 16px; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; }}
            ul {{ margin: 0; padding-left: 20px; }}
            .footer {{ text-align: center; font-size: 12px; color: #94a3b8; padding: 16px; border-top: 1px solid #e2e8f0; background: #fafafa; }}
            p {{ margin: 6px 0; font-size: 14px; line-height: 1.5; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0; font-size: 24px; font-weight: 700;">☀️ Morning Briefing</h1>
                <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.9;">{data['city']} • {data['date_str']}</p>
            </div>
            <div class="content">
                <div class="card">
                    <h2>🌡️ Weather & Environment</h2>
                    <p><b>Temperature:</b> {data['temp']}°C (Feels like: {data['feels_like']}°C)</p>
                    <p><b>Condition:</b> {data['description']}</p>
                    <p><b>Humidity:</b> {data['humidity']}%</p>
                    <p><b>Air Quality (AQI):</b> {data['aqi_status']}</p>
                </div>
                
                <div class="tips-card">
                    <h2>💡 Daily Tips</h2>
                    <p>{data['umbrella_tip']}</p>
                    <p>{data['clothing_tip']}</p>
                </div>

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
    print("HTML weather and schedule email sent successfully!")

if __name__ == "__main__":
    weather_data = get_weather_data()
    send_email(weather_data)
