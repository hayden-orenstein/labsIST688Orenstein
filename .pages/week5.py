import streamlit as st
from openai import OpenAI
import requests
import json


st.title("Lab 5 - What to Wear Bot")

st.write(
    "Enter a city to get today's weather, clothing recommendations, "
    "and suggestions for outdoor activities."
)


if "openai_client" not in st.session_state:
    st.session_state.openai_client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


def get_current_weather(location):

    url = f"https://wttr.in/{location}?format=j1"

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

        chance_of_rain = int(
            hour["chanceofrain"]
        )

        chance_of_snow = int(
            hour["chanceofsnow"]
        )

        precipitation = float(
            hour["precipMM"]
        )


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


    matched_city = (
        data["nearest_area"][0]["areaName"][0]["value"]
    )

    matched_region = (
        data["nearest_area"][0]["region"][0]["value"]
    )

    matched_country = (
        data["nearest_area"][0]["country"][0]["value"]
    )


    return {
        "location_requested": location,

        "location": (
            f"{matched_city}, "
            f"{matched_region}, "
            f"{matched_country}"
        ),

        "temperature_f": float(
            current["temp_F"]
        ),

        "feels_like_f": float(
            current["FeelsLikeF"]
        ),

        "condition": (
            current["weatherDesc"][0]["value"]
        ),

        "high_f": float(
            today["maxtempF"]
        ),

        "low_f": float(
            today["mintempF"]
        ),

        "precipitation_expected": precipitation_expected,

        "precipitation_type": precipitation_type,

        "current_precipitation_mm": float(
            current["precipMM"]
        ),

        "max_chance_of_rain": max_chance_of_rain,

        "max_chance_of_snow": max_chance_of_snow,

        "wind_speed_mph": float(
            current["windspeedMiles"]
        ),

        "humidity": int(
            current["humidity"]
        )
    }


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",

            "description": (
                "Gets the current weather and today's forecast "
                "for a city so that clothing and outdoor activity "
                "recommendations can be made."
            ),

            "parameters": {
                "type": "object",

                "properties": {
                    "location": {
                        "type": "string",

                        "description": (
                            "The city and state or country to get "
                            "weather for, such as Syracuse, NY "
                            "or Lima, Peru."
                        )
                    }
                },

                "required": [
                    "location"
                ]
            }
        }
    }
]


def call_openai(messages, tools=None, tool_choice=None):

    if tools is not None:

        response = (
            st.session_state.openai_client.chat.completions.create(
                model="gpt-5.6-luna",
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                reasoning_effort="none"
            )
        )

    else:

        response = (
            st.session_state.openai_client.chat.completions.create(
                model="gpt-5.6-luna",
                messages=messages,
                reasoning_effort="none"
            )
        )

    return response


city = st.text_input(
    "Enter a city",
    placeholder="Syracuse, NY"
)


if st.button("Get Recommendation"):

    if city.strip() == "":
        city = "Syracuse, NY"


    system_prompt = """
You are a What to Wear assistant.

You MUST use the get_current_weather tool before giving the user
weather, clothing, or outdoor activity advice.

The user will provide a city. Get the current weather and today's
forecast for that city using the tool.

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

Also mention the day's temparture range and other weasther factors like wind and
Precipitation that may affect how the user dresses throughout the day.

Also recommend 2 or 3 outdoor activities that make sense for the
weather.

Keep the answer concise and easy to read.
"""


    messages = [
        {
            "role": "system",
            "content": system_prompt
        },

        {
            "role": "user",
            "content": (
                f"What should I wear today in {city}? "
                f"Also suggest some outdoor activities."
            )
        }
    ]


    try:

        first_response = call_openai(
            messages,
            tools=tools,
            tool_choice="auto"
        )


        response_message = (
            first_response.choices[0].message
        )


        tool_calls = (
            response_message.tool_calls
        )


        if tool_calls:

            messages.append(
                response_message.model_dump(
                    exclude_none=True
                )
            )


            weather_info = None


            for tool_call in tool_calls:

                tool_function = (
                    tool_call.function.name
                )


                if tool_function == "get_current_weather":

                    function_arguments = json.loads(
                        tool_call.function.arguments
                    )


                    location = (
                        function_arguments.get(
                            "location",
                            "Syracuse, NY"
                        )
                    )


                    weather_info = get_current_weather(
                        location
                    )


                    messages.append(
                        {
                            "role": "tool",

                            "tool_call_id": (
                                tool_call.id
                            ),

                            "content": json.dumps(
                                weather_info
                            )
                        }
                    )


            if weather_info is not None:

                final_response = call_openai(
                    messages
                )


                answer = (
                    final_response
                    .choices[0]
                    .message
                    .content
                )


                st.subheader(
                    weather_info["location"]
                )


                st.write(
                    f"**Current:** "
                    f"{weather_info['temperature_f']:.0f}°F"
                )


                st.write(
                    f"**Feels like:** "
                    f"{weather_info['feels_like_f']:.0f}°F"
                )


                st.write(
                    f"**Conditions:** "
                    f"{weather_info['condition']}"
                )


                st.write(
                    f"**High / Low:** "
                    f"{weather_info['high_f']:.0f}°F / "
                    f"{weather_info['low_f']:.0f}°F"
                )


                st.write(
                    f"**Rain chance:** "
                    f"{weather_info['max_chance_of_rain']}%"
                )


                st.write(
                    f"**Snow chance:** "
                    f"{weather_info['max_chance_of_snow']}%"
                )


                st.subheader(
                    "What to Wear"
                )


                st.write(
                    answer
                )


        else:

            st.error(
                "The weather tool was not called. "
                "Please try again."
            )


    except Exception as e:

        st.error(
            f"Error: {e}"
        )