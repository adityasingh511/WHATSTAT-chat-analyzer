import re
import pandas as pd


def preprocessor(data):

    # ---------------------------------------------------------
    # 1. Detect WhatsApp message timestamps
    # Supports:
    # 07/12/2025, 00:06 - Name: Message
    # 07/12/25, 12:06 am - Name: Message
    # 07/12/25, 9:45 pm - Name: Message
    # 07/12/25, 12:06:32 - Name: Message
    # [07/12/25, 12:06:32] Name: Message
    # 07-12-2025, 12:06 PM - Name: Message
    # ---------------------------------------------------------

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

            # Save previous message
            if current_date is not None:
                dates.append(current_date)
                messages.append("\n".join(current_message).strip())

            current_date = f"{match.group(1)}, {match.group(2)}"
            current_message = [line[match.end():]]

        else:

            # Continuation of previous message
            if current_date is not None:
                current_message.append(line)

    # Save final message
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

        date_part = date_part.strip()
        time_part = time_part.strip()

        # Normalize separators
        date_part = date_part.replace("-", "/")

        parts = date_part.split("/")

        if len(parts) != 3:
            return pd.NaT

        try:
            a, b, c = map(int, parts)
        except ValueError:
            return pd.NaT

        if len(parts[0]) == 4:
            # YYYY/MM/DD
            year, month, day = a, b, c

        elif a > 12:
            # DD/MM/YYYY
            day, month, year = a, b, c

        elif b > 12:
            # MM/DD/YYYY
            month, day, year = a, b, c

        else:
            # Ambiguous -> WhatsApp exports are commonly
            # DD/MM in our target data.
            day, month, year = a, b, c

        # Convert 2-digit year
        if year < 100:
            year += 2000

        # -----------------------------------------------------
        # Parse time
        # -----------------------------------------------------

        time_part = time_part.upper().strip()

        time_formats = [
            "%H:%M:%S",
            "%H:%M",
            "%I:%M:%S %p",
            "%I:%M %p",
        ]

        for time_fmt in time_formats:

            try:

                parsed_time = pd.to_datetime(
                    time_part,
                    format=time_fmt
                )

                return pd.Timestamp(
                    year=year,
                    month=month,
                    day=day,
                    hour=parsed_time.hour,
                    minute=parsed_time.minute,
                    second=parsed_time.second
                )

            except (ValueError, TypeError):
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