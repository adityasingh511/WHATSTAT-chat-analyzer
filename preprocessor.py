import re
import pandas as pd


def preprocessor(data):
    # Supports:
    # 07/12/2025, 00:06 - Name: Message
    # 07/12/25, 12:06 am - Name: Message
    # 07/12/25, 9:45 pm - Name: Message
    pattern = r'(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?)\s*-\s*'

    parts = re.split(pattern, data)

    messages = []
    dates = []

    # Skip first part
    for i in range(1, len(parts), 2):
        dates.append(parts[i])
        messages.append(parts[i + 1].strip())

    df = pd.DataFrame({
        "message_date": dates,
        "user_message": messages
    })

    # Convert both 24-hour and 12-hour formats
    def parse_date(value):
        value = re.sub(r'\s+', ' ', value.strip())

        for fmt in (
            "%d/%m/%Y, %H:%M",      
            "%d/%m/%y, %H:%M",      
            "%d/%m/%y, %I:%M %p",   
            "%d/%m/%Y, %I:%M %p",   
            ):
            try:
                return pd.to_datetime(value, format=fmt)
            except ValueError:
                pass

        return pd.NaT

    df["message_date"] = df["message_date"].apply(parse_date)

    # Remove anything that could not be parsed
    df.dropna(subset=["message_date"], inplace=True)

    df.rename(columns={"message_date": "date"}, inplace=True)

    users = []
    chats = []

    for message in df["user_message"]:

        entry = re.match(r"([^:]+):\s(.*)", message, flags=re.DOTALL)

        if entry:
            users.append(entry.group(1).strip())
            chats.append(entry.group(2).strip())
        else:
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
    df["only_date"] = df["date"].dt.date

    return df