import re
import pandas as pd


def preprocessor(data):
    # Pattern for current WhatsApp export format:
    # 14/08/2024, 17:20 - ...
    pattern = r'(\d{1,2}/\d{1,2}/\d{4},\s\d{1,2}:\d{2})\s-\s'

    parts = re.split(pattern, data)

    messages = []
    dates = []

    # Skip first empty part
    for i in range(1, len(parts), 2):
        dates.append(parts[i])
        messages.append(parts[i + 1].strip())

    df = pd.DataFrame({
        "message_date": dates,
        "user_message": messages
    })

    # Convert date column
    df["message_date"] = pd.to_datetime(
        df["message_date"],
        format="%d/%m/%Y, %H:%M"
    )

    df.rename(columns={"message_date": "date"}, inplace=True)

    users = []
    chats = []

    for message in df["user_message"]:

        # Matches: Yashh: Hello
        entry = re.match(r"([^:]+):\s(.*)", message, flags=re.DOTALL)

        if entry:
            users.append(entry.group(1).strip())
            chats.append(entry.group(2).strip())
        else:
            # System notification
            users.append("group_notification")
            chats.append(message)

    df["user"] = users
    df["message"] = chats

    df.drop(columns=["user_message"], inplace=True)

    # Date features
    df["year"] = df["date"].dt.year
    df["month_num"] = df["date"].dt.month
    df["month"] = df["date"].dt.month_name()
    df["day"] = df["date"].dt.day
    df["day_name"] = df["date"].dt.day_name()
    df["hour"] = df["date"].dt.hour
    df["minute"] = df["date"].dt.minute
    df["only_date"]=df["date"].dt.date
    

    return df