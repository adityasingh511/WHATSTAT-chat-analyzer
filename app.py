from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import base64
import io
from pathlib import Path

import preprocessor
import helper

app = Flask(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent / "Frontend"


def dataframe_records(df, columns):
    """Convert selected dataframe columns into JSON-safe records."""
    if df is None or df.empty:
        return []

    out = df[columns].copy()

    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].astype(str)
        else:
            out[col] = out[col].apply(
                lambda value: value.item()
                if hasattr(value, "item")
                else value
            )

    return out.to_dict(orient="records")


def make_wordcloud_base64(selected_user, df):
    """Create the same word cloud used by the existing analyzer."""
    try:
        image = helper.create_wordcloud(selected_user, df)

        buffer = io.BytesIO()
        image.to_image().save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


def build_analysis(selected_user, df):
    """Build all analysis data used by analysis.html."""
    num_messages, num_words, num_media, num_links = helper.fetch_stats(
        selected_user, df
    )

    monthly = helper.monthly_timeline(selected_user, df)
    daily = helper.daily_timeline(selected_user, df)
    weekly = helper.weekly_activity_map(selected_user, df)
    monthly_activity = helper.monthly_activity_map(selected_user, df)
    hourly_activity = helper.hourly_activity_map(selected_user, df)

    common_words = helper.most_common_words(selected_user, df)
    emoji_df = helper.emoji_helper(selected_user, df)
    wordcloud = make_wordcloud_base64(selected_user, df)

    users = [
        str(user)
        for user in df["user"].dropna().unique().tolist()
        if str(user) != "group_notification"
    ]
    users.sort()

    result = {
        "selected_user": selected_user,
        "users": ["Overall"] + users,
        "stats": {
            "messages": int(num_messages),
            "words": int(num_words),
            "media": int(num_media),
            "links": int(num_links),
        },

        "monthly_timeline": dataframe_records(
            monthly, ["time", "message"]
        ),

        "daily_timeline": dataframe_records(
            daily, ["only_date", "message"]
        ),

        "busy_day": dataframe_records(
            weekly, ["day_name", "message"]
        ),

        "busy_month": dataframe_records(
            monthly_activity, ["month", "message"]
        ),

        "hourly_activity": dataframe_records(
            hourly_activity, ["day_name", "hour", "message"]
        ),

        "common_words": dataframe_records(
            common_words, ["Word", "Count"]
        ),

        "emojis": dataframe_records(
            emoji_df, ["Emoji", "Count", "Name"]
        ),

        "wordcloud": wordcloud,
    }

    # Most-busy-user data is meaningful for Overall.
    if selected_user == "Overall":
        busy_users, busy_user_percent = helper.most_busy_users(df)

        result["busy_users"] = [
            {
                "name": str(name),
                "messages": int(count)
            }
            for name, count in busy_users.items()
        ]

        result["busy_user_percent"] = dataframe_records(
            busy_user_percent, ["name", "percent"]
        )
    else:
        result["busy_users"] = []
        result["busy_user_percent"] = []

    return result


@app.get("/")
def home():
    # Keep the current Stitch landing page filename if you haven't renamed it.
    if (FRONTEND_DIR / "preview.html").exists():
        return send_from_directory(FRONTEND_DIR, "preview.html")
    return "Frontend preview.html not found.", 404


@app.get("/analysis.html")
def analysis_page():
    if (FRONTEND_DIR / "analysis.html").exists():
        return send_from_directory(FRONTEND_DIR, "analysis.html")
    return "analysis.html not found. Put your Stitch analysis page inside Frontend/.", 404


@app.get("/preview.html")
def preview_page():
    if (FRONTEND_DIR / "preview.html").exists():
        return send_from_directory(FRONTEND_DIR, "preview.html")

    # Support the current filename while you are transitioning.
    if (FRONTEND_DIR / "preview_auto_redirect.html").exists():
        return send_from_directory(FRONTEND_DIR, "preview_auto_redirect.html")

    return "preview.html not found.", 404


@app.post("/api/analyze")
def analyze():
    uploaded_file = request.files.get("file")

    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "No .txt file was uploaded."}), 400

    if not uploaded_file.filename.lower().endswith(".txt"):
        return jsonify({"error": "Only .txt WhatsApp exports are supported."}), 400

    try:
        raw_data = uploaded_file.read().decode("utf-8")
        df = preprocessor.preprocessor(raw_data)
        

        if df.empty:
            return jsonify({"error": "No WhatsApp messages were detected."}), 400

        users = [
            str(user)
            for user in df["user"].dropna().unique().tolist()
            if str(user) != "group_notification"
        ]
        users.sort()

        # Calculate Overall immediately so the frontend has data on first load.
        overall = build_analysis("Overall", df)

        # Cache the dataframe for this browser session using a simple server-side
        # in-memory store. For a prototype this is enough; later we can replace it
        # with a proper session/database approach.
        analysis_id = str(id(df))

        app.config.setdefault("analysis_store", {})
        app.config["analysis_store"][analysis_id] = df

        return jsonify({
            "success": True,
            "analysis_id": analysis_id,
            "filename": uploaded_file.filename,
            "users": ["Overall"] + users,
            "overall": overall
        })

    except UnicodeDecodeError:
        return jsonify({
            "error": "The file could not be decoded as UTF-8."
        }), 400

    except Exception as exc:
        app.logger.exception("Analysis failed")
        return jsonify({
            "error": f"Analysis failed: {str(exc)}"
        }), 500


@app.get("/api/analyze/<analysis_id>")
def get_analysis(analysis_id):
    store = app.config.get("analysis_store", {})
    df = store.get(analysis_id)

    if df is None:
        return jsonify({
            "error": "Analysis session not found. Please upload the chat again."
        }), 404

    selected_user = request.args.get("user", "Overall")

    available_users = set(
        str(user)
        for user in df["user"].dropna().unique().tolist()
    )

    if selected_user != "Overall" and selected_user not in available_users:
        return jsonify({"error": "Unknown user."}), 400

    try:
        return jsonify({
            "success": True,
            **build_analysis(selected_user, df)
        })
    except Exception as exc:
        app.logger.exception("User analysis failed")
        return jsonify({
            "error": f"User analysis failed: {str(exc)}"
        }), 500


@app.get("/<path:filename>")
def frontend_files(filename):
    # Lets analysis.html load local assets if Stitch creates them.
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
