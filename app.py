from __future__ import annotations

import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from database import clear_scans, create_scan, delete_scan, get_history, get_scan, get_statistics, initialize_database
from news_detector import analyze_news
from utils import ALLOWED_VIDEO_EXTENSIONS, MAX_TEXT_LENGTH, MAX_VIDEO_BYTES, allowed_video_file
from video_detector import analyze_video


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder="templates")
app.config.update(
    MAX_CONTENT_LENGTH=MAX_VIDEO_BYTES,
    JSON_SORT_KEYS=False,
)
initialize_database()


def api_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/news")
def news_page():
    return render_template("news.html")


@app.get("/video")
def video_page():
    return render_template("video.html", allowed_extensions=", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS)))


@app.get("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.get("/history")
def history_page():
    return render_template("history.html")


@app.get("/about")
def about_page():
    return render_template("about.html")


@app.post("/api/analyze-news")
def analyze_news_api():
    payload = request.get_json(silent=True) or {}
    headline = str(payload.get("headline", "")).strip()
    article = str(payload.get("article", "")).strip()
    combined_length = len(headline) + len(article)

    if not headline and not article:
        return api_error("Enter a headline or article before running the analysis.")
    if combined_length > MAX_TEXT_LENGTH:
        return api_error(f"Please keep the combined text below {MAX_TEXT_LENGTH:,} characters.")

    try:
        result = analyze_news(headline, article)
        input_name = headline[:180] if headline else "Article analysis"
        scan_id = create_scan(
            scan_type="news",
            input_name=input_name,
            result=result["label"],
            confidence=result["confidence"],
            risk=result["risk"],
            details=result,
        )
        return jsonify({"ok": True, "scan_id": scan_id, "analysis": result})
    except Exception:
        return api_error("The news analysis could not be completed. Please try a shorter piece of text.", 500)


@app.post("/api/analyze-video")
def analyze_video_api():
    upload = request.files.get("video")
    if upload is None or not upload.filename:
        return api_error("Choose a video file before starting baseline visual analysis.")
    if not allowed_video_file(upload.filename):
        allowed = ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        return api_error(f"Unsupported video format. Choose one of: {allowed}.")

    original_name = secure_filename(upload.filename)
    suffix = Path(original_name).suffix.lower()
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=UPLOAD_DIR, suffix=suffix, delete=False) as temporary_file:
            temp_path = Path(temporary_file.name)
            upload.save(temporary_file)

        if temp_path.stat().st_size == 0:
            return api_error("The uploaded file was empty. Please choose a valid video.")
        if temp_path.stat().st_size > MAX_VIDEO_BYTES:
            return api_error("The video exceeds the 50 MB upload limit.")

        result = analyze_video(temp_path)
        scan_id = create_scan(
            scan_type="video",
            input_name=original_name[:180],
            result=result["label"],
            confidence=result["confidence"],
            risk=result["risk"],
            details=result,
        )
        return jsonify({"ok": True, "scan_id": scan_id, "analysis": result})
    except ValueError as error:
        return api_error(str(error))
    except Exception:
        return api_error("The video could not be analyzed. It may be corrupted or encoded in an unsupported way.", 500)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@app.get("/api/statistics")
def statistics_api():
    try:
        return jsonify({"ok": True, "statistics": get_statistics()})
    except Exception:
        return api_error("Statistics are temporarily unavailable. Please refresh the page.", 500)


@app.get("/api/history")
def history_api():
    scan_type = request.args.get("type", "all")
    result = request.args.get("result", "all")
    search = request.args.get("search", "")
    try:
        return jsonify({"ok": True, "scans": get_history(scan_type, result, search)})
    except Exception:
        return api_error("Scan history is temporarily unavailable. Please refresh the page.", 500)


@app.get("/api/scans/<int:scan_id>")
def scan_detail_api(scan_id: int):
    try:
        scan = get_scan(scan_id)
    except Exception:
        return api_error("The stored scan could not be loaded. Please try again.", 500)
    if scan is None:
        return api_error("That scan could not be found.", 404)
    return jsonify({"ok": True, "scan": scan})


@app.post("/api/delete-scan")
def delete_scan_api():
    payload = request.get_json(silent=True) or {}
    try:
        scan_id = int(payload.get("id"))
    except (TypeError, ValueError):
        return api_error("A valid scan identifier is required.")

    if not delete_scan(scan_id):
        return api_error("That scan could not be found.", 404)
    return jsonify({"ok": True})


@app.post("/api/clear-history")
def clear_history_api():
    clear_scans()
    return jsonify({"ok": True})


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    return api_error("The video exceeds the 50 MB upload limit.", 413)


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return api_error("The requested API route was not found.", 404)
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_error):
    if request.path.startswith("/api/"):
        return api_error("An unexpected error occurred. Please try again.", 500)
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
