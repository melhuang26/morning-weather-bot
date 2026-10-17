import os
import requests
import smtplib
from email.message import EmailMessage

# 1. Retrieve secrets and configuration from environment variables (set by GitHub Actions)
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

# Change this to your target city
CITY = "Taipei"
URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric"

def get_weather():
    response = requests.get(URL)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch weather data: {response.text}")
    
    data = response.json()
    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    description = data["weather"][0]["description"]
    humidity = data["main"]["humidity"]
    
    forecast_text = (
        f"Good morning! Here is today's weather forecast for {CITY}:\n\n"
        f"🌡️ Temperature: {temp}°C (Feels like: {feels_like}°C)\n"
        f"☁️ Condition: {description.capitalize()}\n"
        f"💧 Humidity: {humidity}%\n\n"
        f"Have a wonderful day!"
    )
    return forecast_text

def send_email(content):
    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = f"☀️ Morning Weather Update for {CITY}"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS  # Sends it to yourself

    # Connect to Gmail's SMTP server securely
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
    print("Weather email sent successfully!")

if __name__ == "__main__":
    forecast = get_weather()
    send_email(forecast)
