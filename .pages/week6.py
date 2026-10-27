import os
import streamlit as st
import requests
from urllib.parse import quote
from langchain.agents import create_agent


st.title("Lab 6 - What to Wear Bot with LangChain")


os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]


def get_weather_data(location: str = "Syracuse, NY") -> dict:
    """
    Get current weather and today's forecast for a city, state, country,
    zip code, airport code, or landmark. Returns temperature, conditions,
    precipitation, wind, humidity, and other weather information needed
    to recommend clothing and outdoor activities.
    """

    url = f"https://wttr.in/{quote(location, safe='')}?format=j1"

    response = requests.get(
        url,
        timeout=10
    )

    if response.status_code != 200:
        raise Exception(
            f"wttr.in error: status {response.status_code}"
        )

    try:
        data = response.json()

    except ValueError:
        raise Exception(
            f"Could not find a location named {location}"
        )

    current = data["current_condition"][0]
    today = data["weather"][0]
    hourly = today["hourly"]

    max_chance_of_rain = 0
    max_chance_of_snow = 0
    precipitation_expected = False
    precipitation_type = "none"

    for hour in hourly:

        chance_of_rain = int(hour["chanceofrain"])
        chance_of_snow = int(hour["chanceofsnow"])
        precipitation = float(hour["precipMM"])

        if chance_of_rain > max_chance_of_rain:
            max_chance_of_rain = chance_of_rain

        if chance_of_snow > max_chance_of_snow:
            max_chance_of_snow = chance_of_snow

        if precipitation > 0:
            precipitation_expected = True

    if float(current["precipMM"]) > 0:
        precipitation_expected = True

    if float(today["totalSnow_cm"]) > 0:
        precipitation_expected = True
        precipitation_type = "snow"

    elif precipitation_expected:
        precipitation_type = "rain"

    matched_city = data["nearest_area"][0]["areaName"][0]["value"]
    matched_region = data["nearest_area"][0]["region"][0]["value"]
    matched_country = data["nearest_area"][0]["country"][0]["value"]

    return {
        "location_requested": location,
        "location": (
            f"{matched_city}, {matched_region}, {matched_country}"
        ),
        "temperature_f": float(current["temp_F"]),
        "feels_like_f": float(current["FeelsLikeF"]),
        "condition": current["weatherDesc"][0]["value"],
        "high_f": float(today["maxtempF"]),
        "low_f": float(today["mintempF"]),
        "precipitation_expected": precipitation_expected,
        "precipitation_type": precipitation_type,
        "current_precipitation_mm": float(current["precipMM"]),
        "max_chance_of_rain": max_chance_of_rain,
        "max_chance_of_snow": max_chance_of_snow,
        "wind_speed_mph": float(current["windspeedMiles"]),
        "humidity": int(current["humidity"])
    }


system_prompt = """
You are a What to Wear assistant.

You MUST use the get_weather_data tool before providing weather,
clothing, or outdoor activity advice.

If the user does not provide a location, use Syracuse, NY.

If the user provides multiple locations, call the weather tool
separately for each location and provide recommendations for each.

After receiving the weather information, recommend clothing using
these rules:

PRECIPITATION RULES:

If precipitation is expected and the temperature is below 32°F:
- Recommend a winter jacket and long pants.

If precipitation is expected and the temperature is 32°F or warmer:
- Recommend a rain jacket and clothing appropriate for the temperature.

NO PRECIPITATION RULES:

If there is no precipitation and the temperature is 65°F or warmer:
- Recommend shorts and a t-shirt.

If there is no precipitation and the temperature is between
55°F and 64°F:
- Recommend a sweatshirt and shorts.

If there is no precipitation and the temperature is above
32°F through 54°F:
- Recommend a hoodie and long pants.

If there is no precipitation and the temperature is 32°F or colder:
- Recommend a jacket and long pants.

Use the current temperature for the main clothing recommendation.

Also mention the day's temperature range and other weather factors
like wind and precipitation that may affect how the user dresses
throughout the day.

Recommend 2 or 3 outdoor activities appropriate for the weather.

Only use weather information provided by the tool.
Keep the response concise and easy to read.
"""


agent = create_agent(
    model="openai:gpt-5-mini",
    tools=[get_weather_data],
    system_prompt=system_prompt
)


location = st.text_input(
    "Enter a city",
    placeholder="Syracuse, NY"
)


if st.button("Get advice"):

    if location.strip() == "":
        location = "Syracuse, NY"

    try:

        with st.spinner("Checking the weather..."):

            result = agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                f"What should I wear today in {location}? "
                                f"Also suggest some outdoor activities."
                            )
                        }
                    ]
                }
            )

        answer = result["messages"][-1].content

        with st.chat_message("assistant"):
            st.write(answer)

        with st.expander("Behind the scenes"):

            for message in result["messages"]:

                st.write(f"**{message.type}**")
                st.write(message.content)

                if message.type == "ai" and message.tool_calls:
                    st.write(message.tool_calls)

            weather_lookups = sum(
                1 for message in result["messages"]
                if message.type == "tool"
            )

            model_calls = sum(
                1 for message in result["messages"]
                if message.type == "ai"
            )

            st.write(f"**Weather lookups:** {weather_lookups}")
            st.write(f"**Model calls:** {model_calls}")

    except Exception as e:
        st.error(f"Error: {e}")