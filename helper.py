import re
from wordcloud import WordCloud
import pandas as pd
from collections import Counter
import emoji
def fetch_stats(selected_user , df):

    if selected_user != 'Overall':
        df = df[df['user']==selected_user]

    #fetch number of messages

    num_messages = df.shape[0]

    #fetch number of words
    words= []
    for message in df['message']:
        words.extend(message.split())
    #fetch number of media used
    num_media = df[df['message'] == '<Media omitted>'].shape[0]

    #fetch number of links
    links = []

    for message in df["message"]:
        links.extend(re.findall(r'https?://\S+', message))

    num_links = len(links)


    return num_messages , len(words) , num_media , num_links
def most_busy_users(df):
    x = df['user'].value_counts().head(20)
    percentages = round(
        (df['user'].value_counts()/df.shape[0])*100,2).reset_index()
    percentages.columns = ["name","percent"]
    
    
    return x,percentages
def create_wordcloud(selected_user, df):
    if selected_user != "Overall":
        df = df[df["user"] == selected_user]

    df = df[~df["message"].str.contains(
        "Media omitted", case=False, na=False
    )]

    # Combine messages
    text = df["message"].str.cat(sep=" ")

    # Get words from latest to oldest
    words = re.findall(r"[A-Za-z]+", text.lower())

    # Keep the latest 200 UNIQUE words
    unique_words = []
    seen = set()

    for word in reversed(words):
        if word not in seen:
            seen.add(word)
            unique_words.append(word)

        if len(unique_words) == 300:
            break

    # Reverse again so their original order is maintained
    unique_words.reverse()

    # Generate word cloud using only those 200 words
    limited_text = " ".join(unique_words)

    wc = WordCloud(
        width=1400,
        height=800,
        min_font_size=14,
        max_words=200,
        background_color="white"
    )

    df_wc = wc.generate(limited_text)

    return df_wc
def most_common_words(selected_user, df):

    with open("stop_words.txt","r") as f:
        stop_words = set(f.read().splitlines())

    if selected_user != "Overall":
        df = df[df["user"] == selected_user]

    df = df[df["user"] != "group_notification"]
    df = df[df["message"] != "<Media omitted>"]

    words = []

    for message in df["message"]:

        for word in message.lower().split():

            # Remove punctuation
            word = re.sub(r'[^a-z0-9]', '', word)

            if word == "":
                continue

            if word in stop_words:
                continue

            words.append(word)

    common_df = pd.DataFrame(
        Counter(words).most_common(20),
        columns=["Word","Count"]
    )

    return common_df
def emoji_helper(selected_user, df):

    if selected_user != "Overall":
        df = df[df["user"] == selected_user]

    emojis = []

    for message in df["message"]:
        emojis.extend([c for c in message if c in emoji.EMOJI_DATA])

    emoji_df = pd.DataFrame(
        Counter(emojis).most_common(),
        columns=["Emoji", "Count"]
    )

    emoji_df["Name"] = emoji_df["Emoji"].apply(
        lambda value: emoji.demojize(value).strip(":").replace("_", " ")
    )

    return emoji_df
def monthly_timeline(selected_user , df):

    if selected_user != "Overall":
        df = df[df['user'] == selected_user]

    timeline = df.groupby(['year','month_num','month']).count()['message'].reset_index()
    time = []
    for i in range(timeline.shape[0]):
        time.append(
            timeline['month'][i] + "-" + str(timeline['year'][i]))
    timeline['time'] = time
    return timeline
def daily_timeline(selected_user , df):
    if selected_user != "Overall":
        df = df[df['user']==selected_user]
    timeline = df.groupby('only_date').count()['message'].reset_index()

    return timeline
def weekly_activity_map(selected_user,df):
    if selected_user!= "Overall":
        df = df[df['user']== selected_user]
    timeline = df.groupby("day_name").count()['message'].reset_index()

    return timeline
def monthly_activity_map(selected_user , df):
    if selected_user!= "Overall":
        df = df[df['user']== selected_user]
    timeline = df.groupby("month").count()["message"].reset_index()
    return timeline

    



def hourly_activity_map(selected_user, df):
    if selected_user != "Overall":
        df = df[df["user"] == selected_user]

    return (
        df.groupby(["day_name", "hour"])
        .count()["message"]
        .reset_index()
    )
