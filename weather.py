import os
import requests
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from icalendar import Calendar

# Retrieve secrets
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
CALENDAR_ICS_URL = os.environ.get("CALENDAR_ICS_URL")

CITY = "Taipei"

def get_calendar_events():
    if not CALENDAR_ICS_URL:
        return "📅 Calendar: No calendar URL configured."
    
    try:
        response = requests.get(CALENDAR_ICS_URL)
        if response.status_code != 200:
            return "📅 Calendar: Could not fetch calendar events."
        
        cal = Calendar.from_ical(response.content)
        today = datetime.now().date()
        todays_events = []

        for component in cal.walk():
            if component.name == "VEVENT":
                summary = component.get("summary")
                dtstart = component.get("dtstart")
                
                if dtstart:
                    start_dt = dtstart.dt
                    # Handle all-day events vs timed events
                    if isinstance(start_dt, datetime):
                        event_date = start_dt.date()
                        time_str = start_dt.strftime("%H:%M")
                    else:
                        event_date = start_dt
                        time_str = "All-day"
                    
                    if event_date == today:
                        todays_events.append(f"• {time_str} - {summary}")

        if not todays_events:
            return "📅 Today's Schedule: No events scheduled for today! Enjoy your free time."
        
        return "📅 Today's Schedule:\n" + "\n".join(todays_events)
    except Exception as e:
        return f"📅 Calendar Error: Could not parse events ({str(e)})"

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
    tips = []
    rain_keywords = ["rain", "drizzle", "thunderstorm", "shower"]
    if any(keyword in description.lower() for keyword in rain_keywords):
        tips.append("☔ Umbrella Alert: Rain expected, don't forget an umbrella!")
    else:
        tips.append("☀️ No rain expected—leave the umbrella at home.")
        
    if temp < 18:
        tips.append("🧥 Clothing Tip: It's chilly today! Wear a heavy coat or warm sweater.")
    elif 18 <= temp <= 25:
        tips.append("👕 Clothing Tip: Moderate weather! A long-sleeve shirt or light layer is perfect.")
    else:
        tips.append("👕 Clothing Tip: Warm weather! Wear light, breathable clothes.")
    return "\n".join(tips)

def get_weather():
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
    tips = get_clothing_and_umbrella_tips(temp, description)
    schedule_text = get_calendar_events()
    
    forecast_text = (
        f"Good morning! Here is your daily briefing for {CITY}:\n\n"
        f"🌡️ Temperature: {temp}°C (Feels like: {feels_like}°C)\n"
        f"☁️ Condition: {description.capitalize()}\n"
        f"💧 Humidity: {humidity}%\n"
        f"🍃 Air Quality (AQI): {aqi_status}\n\n"
        f"--- Daily Tips ---\n"
        f"{tips}\n\n"
        f"--- Schedule ---\n"
        f"{schedule_text}\n\n"
        f"Have a wonderful day!"
    )
    return forecast_text

def send_email(content):
    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = f"☀️ Morning Briefing & Schedule for {CITY}"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
    print("Weather and schedule email sent successfully!")

if __name__ == "__main__":
    forecast = get_weather()
    send_email(forecast)
