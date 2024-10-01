import telebot
import requests
from telebot import types
import time
from threading import Thread
from datetime import datetime, timedelta

BOT_TOKEN = '6888273732:AAEvbTncoC_EfSzGLWPxbzDv0ANWUaJAZ_4'
bot = telebot.TeleBot(BOT_TOKEN)

# Global variables
subscribed_users = set()  # Store all the users who interact with the bot
tick_data = {}  # Store ticks data with timestamp

# Message handler for top changes
@bot.message_handler(commands=['top_changes'])
def show_top_changes(message):
    handle_top_change(message.chat.id)

# Message handler for top ticks
@bot.message_handler(commands=['top_ticks'])
def show_top_ticks(message):
    handle_top_ticks(message.chat.id)

# Track users who interact with the bot
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    subscribed_users.add(chat_id)  # Track the users
    bot.send_message(chat_id, "Welcome! You are now subscribed to updates.")

# Callback handler for inline buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == 'top_ticks':
        handle_top_ticks(chat_id)
    elif data == 'top_change':
        handle_top_change(chat_id)
    else:
        bot.send_message(chat_id, "Unknown option.")

# Function to fetch and display top ticks
def handle_top_ticks(chat_id):
    api_url = 'https://orionterminal.com/api/screener'
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        items = data.items()
        sorted_items = sorted(items, key=lambda x: x[1].get('17', float('-inf')), reverse=True)
        top_5_items = sorted_items[:5]

        message_parts = []
        message_parts.append(f"🪙 Top 5 By Ticks by last 5 minutes")
        for key, values in top_5_items:
            value = values.get('17', 'no_value')    
            message_parts.append(f"{key.split('-')[0]}  :  {value}")

        response_message = "\n".join(message_parts)
    except Exception as e:
        response_message = f"Error occurred: {str(e)}"

    bot.send_message(chat_id, response_message)

# Function to fetch and display top changes
def handle_top_change(chat_id):
    api_url = 'https://orionterminal.com/api/screener'
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        items = data.items()
        sorted_items = sorted(items, key=lambda x: x[1].get('1', float('-inf')), reverse=True)
        top_5_items = sorted_items[:5]

        message_parts = []
        message_parts.append(f"🪙 Top 5 Change by last 1d")
        for key, values in top_5_items:
            value = values.get('1', 'no_value')
            message_parts.append(f"{key.split('-')[0]}  :  {value}%")

        response_message = "\n".join(message_parts)
    except Exception as e:
        response_message = f"Error occurred: {str(e)}"

    bot.send_message(chat_id, response_message)

def listener():
    api_url = 'https://orionterminal.com/api/screener'
    while True:
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            current_time = datetime.now()
            growing_items = []
            dumping_items = []
            percentage_changes = []

            for key, values in data.items():
                current_ticks = values.get('17', None)
                change_5m = values.get('3', None)  # Assuming '3' is change_5m
                volume_5m = values.get('26', None)  # Assuming '26' is volume_5m

                if current_ticks is not None:
                    if key in tick_data:
                        last_tick, last_time = tick_data[key]
                        if (current_time - last_time) <= timedelta(hours=1):
                            percentage_change = ((current_ticks - last_tick) / last_tick) * 100
                            if percentage_change > 10:
                                growing_items.append((key, current_ticks, percentage_change))
                                percentage_changes.append((key, current_ticks, percentage_change))

                    tick_data[key] = (current_ticks, current_time)

                if change_5m is not None and volume_5m is not None:
                    if change_5m > 150 and volume_5m > 500000:
                        growing_items.append((key, change_5m, volume_5m))

                    if change_5m < -150 and volume_5m > 500000:
                        dumping_items.append((key, change_5m, volume_5m))

            growing_items = sorted(growing_items, key=lambda x: x[2], reverse=True)[:5]
            dumping_items = sorted(dumping_items, key=lambda x: x[2], reverse=True)[:5]

            if growing_items:
                message_parts = []
                message_parts.append("🔺 Top 5 by Ticks (above 10% increase):")
                for key, current_ticks, percentage_change in growing_items:
                    message_parts.append(f"{key.split('-')[0]} is Up +{percentage_change:.2f}%")

                message_parts.append("\n📈 Top 5 by Percentage Change:")
                for key, current_ticks, percentage_change in sorted(percentage_changes, key=lambda x: x[1], reverse=True)[:5]:
                    message_parts.append(f"{key.split('-')[0]} : {percentage_change:.2f}% ({current_ticks} ticks)")

                response_message = "\n".join(message_parts)

                for user in subscribed_users:
                    bot.send_message(user, response_message)

            if growing_items:
                boost_message_parts = []
                boost_message_parts.append("🚀 Boost Alert:")
                for key, change_5m, volume_5m in growing_items:
                    boost_message_parts.append(f"{key.split('-')[0]}: +{change_5m:.2f}% in the last 5 minutes, volume: {volume_5m}")

                boost_message = "\n".join(boost_message_parts)

                for user in subscribed_users:
                    bot.send_message(user, boost_message)

            if dumping_items:
                dump_message_parts = []
                dump_message_parts.append("📉 Dump Alert:")
                for key, change_5m, volume_5m in dumping_items:
                    dump_message_parts.append(f"{key.split('-')[0]}: {change_5m:.2f}% drop in the last 5 minutes, volume: {volume_5m}")

                dump_message = "\n".join(dump_message_parts)

                for user in subscribed_users:
                    bot.send_message(user, dump_message)

        except requests.exceptions.RequestException as e:
            print(f"Error occurred in listener: {str(e)}")
        
        time.sleep(30)


def send_hello_messages():
    while True:
        for user in subscribed_users:
            bot.send_message(user, "Hello! This is a periodic message.")
        time.sleep(10)

if __name__ == "__main__":
    print("Bot is running...")
    listener_thread = Thread(target=listener)
    listener_thread.start()

    bot.polling(none_stop=True)
