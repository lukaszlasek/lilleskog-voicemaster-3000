#!/usr/bin/env python3
"""Flask web app — Voice Master."""

import json
import queue
import threading
import uuid
from pathlib import Path

from flask import (
    Flask, Response, jsonify, render_template,
    request, send_file, stream_with_context,
)

from master_voice import process_audio
from presets import PRESETS, DEFAULT_PRESET, audio_params

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

JOBS_DIR = Path(__file__).parent / "jobs"
JOBS_DIR.mkdir(exist_ok=True)

jobs: dict[str, dict] = {}

ALLOWED = {".wav", ".flac", ".mp3", ".aiff", ".aif", ".m4a", ".ogg", ".opus"}


# ── routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    suffix = Path(f.filename).suffix.lower()
    if suffix not in ALLOWED:
        return jsonify({"error": f"Unsupported format: {suffix}"}), 400

    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir()

    input_path = job_dir / f"input{suffix}"
    f.save(str(input_path))

    preset_name = request.form.get("preset", DEFAULT_PRESET)
    if preset_name not in PRESETS:
        preset_name = DEFAULT_PRESET

    jobs[job_id] = {
        "started": False,
        "input_path": str(input_path),
        "output_path": str(job_dir / "output.wav"),
        "spec_path": str(job_dir / "spectro.png"),
        "queue": queue.Queue(),
        "original_name": f.filename,
        "preset": preset_name,
    }
    return jsonify({"job_id": job_id})


@app.route("/process/<job_id>")
def process_stream(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    if job["started"]:
        return jsonify({"error": "Already started"}), 409
    job["started"] = True

    def run():
        q = job["queue"]
        preset_name = job.get("preset", DEFAULT_PRESET)
        preset      = PRESETS.get(preset_name, PRESETS[DEFAULT_PRESET])

        def on_status(step, status, detail="", params=None):
            q.put({
                "type": "step", "step": step,
                "status": status, "detail": detail,
                "params": params or {},
            })

        try:
            result = process_audio(
                job["input_path"],
                job["output_path"],
                job["spec_path"],
                preset_label=preset["label"],
                on_status=on_status,
                **audio_params(preset_name),
            )
            q.put({"type": "done", **result})
        except Exception as exc:
            q.put({"type": "error", "message": str(exc)})
        finally:
            q.put(None)

    threading.Thread(target=run, daemon=True).start()

    def generate():
        q = job["queue"]
        while True:
            try:
                msg = q.get(timeout=120)
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"
                continue
            if msg is None:
                break
            yield f"data: {json.dumps(msg)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/result/<job_id>/audio")
def result_audio(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Not found"}), 404
    job = jobs[job_id]
    stem = Path(job["original_name"]).stem
    return send_file(
        job["output_path"],
        as_attachment=True,
        download_name=f"{stem}_mastered.wav",
        mimetype="audio/wav",
    )


@app.route("/result/<job_id>/spectrogram")
def result_spectrogram(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Not found"}), 404
    return send_file(jobs[job_id]["spec_path"], mimetype="image/png")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import webbrowser, threading as _t
    _t.Timer(0.8, lambda: webbrowser.open("http://localhost:5001")).start()
    app.run(host="127.0.0.1", port=5001, debug=False, threaded=True)
