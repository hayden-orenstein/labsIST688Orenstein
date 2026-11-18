
import asyncio
import os
import time
import streamlit as st
import requests
from agents import Agent, Runner, function_tool

st.title("Week 9 - Multi-Agent What to Wear Bot")

st.write(
    "Compare a single AI agent with a team of agents that "
    "work together to provide weather, clothing, and outdoor "
    "activity recommendations."
)

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

MODEL = "gpt-5-mini"


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


@function_tool
def get_weather(location: str = "Syracuse, NY") -> dict:
    """
    Gets current weather and today's forecast for a location.
    Accepts cities with states or countries, such as Syracuse, NY
    or Lima, Peru. Returns temperature, conditions, precipitation,
    wind, humidity, and the location identified by the weather service.
    """
    return get_current_weather(location)


weather_agent = Agent(
    name="Weather agent",
    instructions="""
    You are a weather specialist.

    Always call get_weather to retrieve the current weather and forecast
    for the requested location.

    Summarize the temperature, feels-like temperature, conditions,
    daily high and low, precipitation, wind, and humidity.

    Check that the location returned by the tool makes sense for
    the location requested. If it does not, explain the uncertainty.

    Only provide weather facts. Do not recommend clothing or activities.
    """,
    tools=[get_weather],
    model=MODEL
)


stylist_agent = Agent(
    name="Stylist agent",
    instructions="""
    You are a clothing and fashion specialist.

    Use only the weather information provided by the manager.
    Recommend clothing based on the current temperature.

    PRECIPITATION RULES:

    If precipitation is expected and temperature is below 32°F:
    - Recommend a winter jacket and long pants.

    If precipitation is expected and temperature is 32°F or warmer:
    - Recommend a rain jacket and clothing appropriate for the temperature.

    NO PRECIPITATION RULES:

    If there is no precipitation and temperature is 65°F or warmer:
    - Recommend shorts and a t-shirt.

    If there is no precipitation and temperature is 55°F through 64°F:
    - Recommend a sweatshirt and shorts.

    If there is no precipitation and temperature is above 32°F
    through 54°F:
    - Recommend a hoodie and long pants.

    If there is no precipitation and temperature is 32°F or colder:
    - Recommend a jacket and long pants.

    Mention how wind, precipitation, and the day's temperature range
    might affect what the person should wear.

    Do not invent weather information or recommend activities.
    """,
    model=MODEL
)


activity_agent = Agent(
    name="Activity agent",
    instructions="""
    You are an outdoor activity planner.

    Using only the weather information provided by the manager,
    recommend 2 or 3 outdoor activities appropriate for the weather.

    Consider temperature, precipitation, wind, and current conditions.

    Explain briefly why each activity is appropriate.

    Avoid unsafe outdoor activities in severe conditions.
    Do not invent weather information or provide clothing advice.
    """,
    model=MODEL
)


manager_agent = Agent(
    name="Manager",
    instructions="""
    You manage a team of three specialist agents.

    You MUST follow this workflow:

    1. Call weather_report first to retrieve the weather facts.
    2. Send the relevant weather information to clothing_advice
       and ask for clothing recommendations.
    3. Send the weather information to activity_ideas
       and ask for 2 or 3 outdoor activity suggestions.
    4. Combine their findings into one clear final answer.

    Include:
    - Location and current weather
    - Today's high and low
    - What to wear
    - Suggested outdoor activities

    Do not invent weather facts. If the weather service cannot
    identify the requested location reliably, explain this
    rather than making up recommendations.

    Keep the final answer organized and concise.
    """,
    tools=[
        weather_agent.as_tool(
            tool_name="weather_report",
            tool_description=(
                "Retrieve current weather and today's forecast "
                "for a requested location."
            )
        ),
        stylist_agent.as_tool(
            tool_name="clothing_advice",
            tool_description=(
                "Recommend appropriate clothing using the "
                "weather information supplied."
            )
        ),
        activity_agent.as_tool(
            tool_name="activity_ideas",
            tool_description=(
                "Suggest outdoor activities using the "
                "weather information supplied."
            )
        )
    ],
    model=MODEL
)


single_agent = Agent(
    name="Single agent",
    instructions="""
    You are a What to Wear assistant.

    You MUST call get_weather before providing weather,
    clothing, or outdoor activity recommendations.

    Get the current weather and today's forecast for the location.

    PRECIPITATION RULES:

    If precipitation is expected and temperature is below 32°F:
    - Recommend a winter jacket and long pants.

    If precipitation is expected and temperature is 32°F or warmer:
    - Recommend a rain jacket and clothing appropriate for the temperature.

    NO PRECIPITATION RULES:

    If there is no precipitation and temperature is 65°F or warmer:
    - Recommend shorts and a t-shirt.

    If there is no precipitation and temperature is 55°F through 64°F:
    - Recommend a sweatshirt and shorts.

    If there is no precipitation and temperature is above 32°F
    through 54°F:
    - Recommend a hoodie and long pants.

    If there is no precipitation and temperature is 32°F or colder:
    - Recommend a jacket and long pants.

    Use the current temperature for the main clothing recommendation.

    Also mention today's high and low and other relevant weather
    factors such as precipitation and wind.

    Recommend 2 or 3 outdoor activities suitable for the weather.

    Check that the weather tool identified the requested location.
    If the location cannot be identified reliably, acknowledge that.

    Keep the answer concise and easy to read.
    """,
    tools=[get_weather],
    model=MODEL
)


@st.cache_resource
def get_event_loop():
    return asyncio.new_event_loop()


def run(agent, prompt):

    start = time.perf_counter()

    result = get_event_loop().run_until_complete(
        Runner.run(agent, prompt)
    )

    return result, time.perf_counter() - start


if "week9_results" not in st.session_state:
    st.session_state.week9_results = {}


location = st.text_input(
    "Enter a city",
    placeholder="Syracuse, NY"
)

agent_choice = st.radio(
    "Choose the agent setup",
    ["Single agent", "Team"],
    horizontal=True
)


if st.button("Get advice"):

    if location.strip() == "":
        location = "Syracuse, NY"

    selected_agent = (
        single_agent
        if agent_choice == "Single agent"
        else manager_agent
    )

    prompt = (
        f"What should I wear and do today in {location}?"
    )

    try:

        with st.spinner("Getting recommendations..."):
            result, seconds = run(
                selected_agent,
                prompt
            )

        with st.chat_message("assistant"):
            st.write(result.final_output)

        usage = result.context_wrapper.usage

        with st.expander("Behind the scenes"):

            st.write(
                f"**Model requests:** {usage.requests}"
            )

            st.write(
                f"**Total tokens:** {usage.total_tokens:,}"
            )

            st.write(
                f"**Time:** {seconds:.1f} seconds"
            )

            st.write(
                f"**Answered by:** {result.last_agent.name}"
            )

            st.write("**Tool calls and results:**")

            for item in result.new_items:

                if item.type == "tool_call_item":

                    st.write(
                        f"{item.agent.name} called "
                        f"{item.raw_item.name}: "
                        f"{item.raw_item.arguments}"
                    )

                elif item.type == "tool_call_output_item":

                    st.write(
                        f"Result: {str(item.output)[:300]}"
                    )

                elif item.type == "handoff_output_item":

                    st.write(
                        f"Handoff: {item.source_agent.name} "
                        f"-> {item.target_agent.name}"
                    )

        st.session_state.week9_results[
            (location, agent_choice)
        ] = {
            "Location": location,
            "Agent": agent_choice,
            "Model requests": usage.requests,
            "Total tokens": usage.total_tokens,
            "Seconds": round(seconds, 1)
        }

    except Exception as e:
        st.error(f"Error: {e}")


if st.session_state.week9_results:

    st.subheader("Single Agent vs. Team Comparison")

    st.table(
        list(st.session_state.week9_results.values())
    )

    st.write(
        "Run both agent setups for Syracuse, NY and Lima, Peru. "
        "Compare the model requests, tokens, execution time, "
        "and quality of the answers."
    )

# Part D
#
# a. The intended order is weather_report first, followed by
# clothing_advice and activity_ideas. 

# b. The weather agent writes a weather summary from the tool
# results. The manager then sends weather information to the
# stylist. It does not have to send the complete raw forecast.
#
# c. Model requests include calls made inside the specialist
# agents, not just the manager's visible tool calls.
# The weather agent calls the model to use the weather tool and
# summarize the result. The stylist and activity agents also
# use the model to create their recommendations.
