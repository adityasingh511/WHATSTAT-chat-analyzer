import re
import pandas as pd

def preprocessor(data):

    # 1. Sanitize the data to replace Unicode spaces with standard spaces
    data = data.replace('\u202f', ' ').replace('\u00A0', ' ')

    timestamp_pattern = re.compile(
        r'^\[?'
        r'(\d{1,4}[/-]\d{1,2}[/-]\d{1,4})'
        r',\s*'
        r'(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)'
        r'\]?\s*(?:-\s*|\s+)'
    )

    dates = []
    messages = []
    current_date = None
    current_message = []

    for line in data.splitlines():
        match = timestamp_pattern.match(line)
        if match:
            if current_date is not None:
                dates.append(current_date)
                messages.append("\n".join(current_message).strip())
            current_date = f"{match.group(1)}, {match.group(2)}"
            current_message = [line[match.end():]]
        else:
            if current_date is not None:
                current_message.append(line)

    if current_date is not None:
        dates.append(current_date)
        messages.append("\n".join(current_message).strip())

    df = pd.DataFrame({
        "message_date": dates,
        "user_message": messages
    })

    def parse_date(value):
        value = re.sub(r'\s+', ' ', value.strip())
        date_part, time_part = value.split(",", 1)
        date_part = date_part.strip().replace("-", "/")
        parts = date_part.split("/")

        if len(parts) != 3:
            return pd.NaT

        try:
            a, b, c = map(int, parts)
        except ValueError:
            return pd.NaT

        if len(parts[0]) == 4:
            year, month, day = a, b, c
        elif a > 12:
            day, month, year = a, b, c
        elif b > 12:
            month, day, year = a, b, c
        else:
            day, month, year = a, b, c

        if year < 100:
            year += 2000

        time_part = time_part.upper().strip()
        time_formats = ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]

        for time_fmt in time_formats:
            try:
                parsed_time = pd.to_datetime(time_part, format=time_fmt)
                return pd.Timestamp(
                    year=year, month=month, day=day,
                    hour=parsed_time.hour, minute=parsed_time.minute, second=parsed_time.second
                )
            except (ValueError, TypeError):
                pass
        return pd.NaT

    # 2. Guardrail: If regex matched nothing, return empty DF cleanly to avoid crashes
    if df.empty:
        return pd.DataFrame(columns=['date', 'user', 'message', 'year', 'month_num', 'month', 'day', 'day_name', 'hour', 'minute', 'only_date'])

    df["message_date"] = df["message_date"].apply(parse_date)
    df.dropna(subset=["message_date"], inplace=True)
    df.rename(columns={"message_date": "date"}, inplace=True)

    # 3. Explicitly convert to datetime so the .dt accessor never fails
    df["date"] = pd.to_datetime(df["date"])

    # Ensure df is still not empty after dropna before proceeding
    if df.empty:
        return pd.DataFrame(columns=['date', 'user', 'message', 'year', 'month_num', 'month', 'day', 'day_name', 'hour', 'minute', 'only_date'])

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