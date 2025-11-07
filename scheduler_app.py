import os
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from make_schedule import load_data, make_schedule, get_schedule_print

app = Flask(__name__)
app.secret_key = os.urandom(24) 
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def parse_text_list(text_input):
    """Helper to parse comma-separated numbers from an entry box."""
    if not text_input:
        return []
    try:
        return [int(x.strip()) for x in text_input.split(',')]
    except ValueError:
        return None # Indicates error

# --- Main HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoName Rehearsal Scheduler</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f7f6;
            color: #333;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            overflow: hidden;
        }
        header {
            padding: 20px 30px;
            background-color: #f8f8f8;
            border-bottom: 1px solid #e0e0e0;
        }
        header h1 {
            margin: 0;
            color: #111;
        }
        .content {
            display: flex;
            flex-wrap: wrap;
        }
        .form-container {
            flex: 1;
            min-width: 320px;
            padding: 30px;
            border-right: 1px solid #e0e0e0;
        }
        .results-container {
            flex: 2.5;
            padding: 30px;
            overflow-x: auto;
        }
        form {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
        }
        .form-group label {
            font-weight: 600;
            margin-bottom: 8px;
        }
        .form-group input[type="text"],
        .form-group input[type="number"],
        .form-group input[type="file"] {
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            font-size: 1rem;
        }
        .form-group input[type="file"] {
            padding: 5px;
        }
        .form-group .actor-list {
            max-height: 150px;
            overflow-y: auto;
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 10px;
            background: #fafafa;
        }
        .form-group .actor-list label {
            display: block;
            font-weight: normal;
            margin-bottom: 5px;
        }
        .form-group .actor-list input {
            margin-right: 8px;
        }
        .btn-submit {
            padding: 12px 20px;
            background-color: #007aff;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .btn-submit:hover {
            background-color: #005bb5;
        }
        
        /* Flashed messages (errors/success) */
        .flash {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            font-weight: 500;
        }
        .flash.success {
            background-color: #e0f8e0;
            border: 1px solid #a0d0a0;
            color: #206020;
        }
        .flash.error {
            background-color: #f8e0e0;
            border: 1px solid #d0a0a0;
            color: #602020;
        }
        .file-status {
            padding: 10px 15px;
            border-radius: 5px;
            background: #e6f7ff;
            border: 1px solid #b3e0ff;
            color: #0056b3;
            margin-bottom: 20px;
        }

        /* Results Styling */
        .summary-box {
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 25px;
        }
        .summary-box h3 {
            margin-top: 0;
        }
        .summary-box p {
            margin: 5px 0;
            font-size: 1.05rem;
        }
        
        /* Added for the breakdown list */
        .summary-box ul {
            margin-top: 5px;
            padding-left: 25px;
            font-size: 0.9em;
            list-style-type: disc;
        }
        .summary-box li {
            margin-bottom: 3px;
        }
        
        /* Table Wrapper for scrolling */
        .schedule-table-wrapper {
            width: 100%;
            overflow-x: auto;
            border: 1px solid #dee2e6;
            border-radius: 5px;
        }

        /* Schedule Table */
        table.data-grid {
            width: 100%;
            border-collapse: collapse;
            min-width: 800px;
        }
        table.data-grid th,
        table.data-grid td {
            padding: 10px 12px;
            border: 1px solid #dee2e6;
            text-align: left;
            white-space: nowrap;
        }
        table.data-grid th {
            background-color: #f8f9fa;
            font-weight: 600;
            /* Sticky headers */
            position: sticky;
            top: 0;
            z-index: 10;
        }
        table.data-grid td:first-child,
        table.data-grid th:first-child {
            font-weight: 600;
            /* Sticky first column */
            position: sticky;
            left: 0;
            z-index: 5;
            background-color: #f8f9fa; /* Match header */
        }
        table.data-grid th:first-child {
            z-index: 11; /* Must be above sticky header */
        }
        table.data-grid tr:nth-child(even) td {
            background-color: #fdfdfd;
        }
        table.data-grid td:not(:first-child) {
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>NoName Rehearsal Scheduler</h1>
        </header>

        <div class="content">
            <div class="form-container">
                <form method="POST" enctype="multipart/form-data">
                    
                    {% with messages = get_flashed_messages(with_categories=true) %}
                        {% if messages %}
                            {% for category, message in messages %}
                                <div class="flash {{ category }}">{{ message }}</div>
                            {% endfor %}
                        {% endif %}
                    {% endwith %}

                    {% if session.get('active_file_short') %}
                    <div class="file-status">
                        <strong>Active File:</strong> {{ session['active_file_short'] }}
                        <br><small>Re-upload only if you want to change this.</small>
                    </div>
                    {% endif %}
                    
                    <div class="form-group">
                        <label for="csv_file">Upload CSV Matrix</label>
                        <input type="file" name="csv_file" id="csv_file" accept=".csv">
                    </div>

                    <div class="form-group">
                        <label for="max_hours">Max Hours (e.g., 8)</label>
                        <input type="number" name="max_hours" id="max_hours" value="{{ request.form.get('max_hours', 8) }}" step="0.5" required>
                    </div>

                    <div class="form-group">
                        <label for="min_hours">Min Hours (e.g., 2)</label>
                        <input type="number" name="min_hours" id="min_hours" value="{{ request.form.get('min_hours', 2) }}" step="0.5" required>
                    </div>

                    <div class="form-group">
                        <label for="include_scenes">Scenes to Include (e.g., 1, 2, 3)</label>
                        <input type="text" name="include_scenes" id="include_scenes" value="{{ request.form.get('include_scenes', '') }}">
                    </div>

                    <div class="form-group">
                        <label for="avoid_scenes">Scenes to Avoid (e.g., 4, 5)</label>
                        <input type="text" name="avoid_scenes" id="avoid_scenes" value="{{ request.form.get('avoid_scenes', '') }}">
                    </div>

                    <div class="form-group">
                        <label>Ignore Actors</label>
                        <div class="actor-list">
                            {% if session.get('actors_list') %}
                                {% for actor in session['actors_list'] %}
                                <label>
                                    <input type="checkbox" name="ignore_actors" value="{{ actor }}"
                                    {% if actor in (request.form.getlist('ignore_actors') or []) %} checked {% endif %}>
                                    {{ actor }}
                                </label>
                                {% endfor %}
                            {% else %}
                                <small>Upload a CSV file to see actor list.</small>
                            {% endif %}
                        </div>
                    </div>

                    <button type="submit" class="btn-submit">Generate Schedule</button>
                </form>
            </div>

            <div class="results-container">
                {% if results %}
                    <div class="summary-box">
                        <h3>Summary</h3>
                        <p><strong>Suggested Scene Order:</strong> {{ results.scenes }}</p>
                        
                        {% if results.breakdown and 'Total Time (min)' in results.breakdown %}
                            <p><strong>Total Rehearsal Time:</strong> {{ "%.1f"|format(results.breakdown["Total Time (min)"] / 60) }} hours ({{ "%.0f"|format(results.breakdown["Total Time (min)"]) }} min)</p>
                        {% endif %}
                        <p><strong>Schedule Quality (Total): {{ "%.0f"|format(results.energy) }}</strong></p>
                        <ul>
                            <li style="color: #444;">(Breakdown of score, lower is better)</li>
                            {% if results.breakdown %}
                                {% for key, value in results.breakdown.items() %}
                                    {% if key != 'Total Time (min)' %} 
                                        {% if value > 0 %}
                                            <li style="color: #b22222;">
                                                <strong>{{ key }}: {{ "%.0f"|format(value) }}</strong>
                                            </li>
                                        {% else %}
                                            <li>{{ key }}: 0</li>
                                        {% endif %}
                                    {% endif %}
                                {% endfor %}
                            {% endif %}
                        </ul>
                        
                        <p><strong>Ignored Actors:</strong> {{ results.ignored_actors_str }}</p>
                        <p><strong>Ignored Scenes:</strong> {{ results.ignored_scenes_str }}</p>
                    </div>
                    
                    <div class="schedule-table-wrapper">
                        {{ results.table | safe }}
                    </div>
                {% else %}
                    <p>Upload a file and click "Generate Schedule" to see results here.</p>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    
    if request.method == 'POST':
        # --- 1. Handle File Upload ---
        file = request.files.get('csv_file')
        
        # Check if a new file was uploaded
        if file and file.filename:
            try:
                # Clear old file if it exists
                if 'active_file_path' in session and os.path.exists(session['active_file_path']):
                    os.remove(session['active_file_path'])

                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Load data to populate actor list
                sa_matrix, actors_list, scene_time = load_data(file_path)
                
                # Store in session
                session['active_file_path'] = file_path
                session['active_file_short'] = filename
                session['actors_list'] = actors_list # For populating checkboxes
                session['sa_matrix'] = sa_matrix.tolist() # Store as list
                session['scene_time'] = scene_time # Store as list
                
                flash(f"Successfully uploaded '{filename}'.", 'success')
                
                # --- THIS IS THE FIX ---
                # REMOVED: return render_template_string(HTML_TEMPLATE)
                # By removing the return, code will "fall through"
                # to the scheduler logic on the same request.
                
            except Exception as e:
                flash(f"Error loading file: {e}", 'error')
                session.pop('active_file_path', None)
                session.pop('active_file_short', None)
                session.pop('actors_list', None)
                session.pop('sa_matrix', None)
                session.pop('scene_time', None)
                # This return IS correct, as a file error should
                # stop the process.
                return render_template_string(HTML_TEMPLATE)

        # --- 2. Check for Active File ---
        if 'active_file_path' not in session or not os.path.exists(session['active_file_path']):
            flash("Please upload a CSV file first.", 'error')
            return render_template_string(HTML_TEMPLATE)
            
        # --- 3. Run Scheduler (if file is active) ---
        # This block will now run on the *same* request as a file upload
        try:
            # Load data from session
            sa_matrix = np.array(session['sa_matrix'])
            actors_list = session['actors_list']
            scene_time = session['scene_time']

            # Parse form inputs
            max_hours = float(request.form['max_hours'])
            min_hours = float(request.form['min_hours'])
            
            include_scenes = parse_text_list(request.form['include_scenes'])
            if include_scenes is None:
                raise ValueError("Invalid format for 'Scenes to Include'. Use comma-separated numbers.")
                
            avoid_scenes = parse_text_list(request.form['avoid_scenes'])
            if avoid_scenes is None:
                raise ValueError("Invalid format for 'Scenes to Avoid'. Use comma-separated numbers.")

            # Get ignored actors (names) from checkboxes
            ignored_actor_names = request.form.getlist('ignore_actors')
            
            # Convert ignored names to 1-based indices for the algorithm
            actors_to_ignore_indices = []
            if ignored_actor_names:
                actor_name_to_index = {name: i + 1 for i, name in enumerate(actors_list)}
                for name in ignored_actor_names:
                    if name in actor_name_to_index:
                        actors_to_ignore_indices.append(actor_name_to_index[name])

            # --- Run the algorithm ---
            best_state, best_energy, call_times, nr_calls, energy_breakdown = make_schedule(
                max_hours=max_hours,
                min_hours=min_hours,
                sa_matrix=sa_matrix,
                scene_time=scene_time,
                actors_list=actors_list,
                actors_to_ignore=actors_to_ignore_indices,
                scenes_to_include=include_scenes,
                scenes_to_avoid=avoid_scenes
            )
            
            # --- Format results for display ---
            schedule_df = get_schedule_print(
                scene_matrix=sa_matrix,
                name_list=actors_list,
                scene_time=scene_time,
                selected_scenes=best_state, # Pass 0-indexed state
                actors_to_ignore=actors_to_ignore_indices # Pass 1-based indices
            )
            
            results = {
                "scenes": ", ".join([str(s + 1) for s in best_state]),
                "energy": best_energy,
                "table": schedule_df.to_html(classes=["data-grid"], border=0),
                "ignored_actors_str": ", ".join(ignored_actor_names) if ignored_actor_names else "None",
                "ignored_scenes_str": ", ".join(map(str, avoid_scenes)) if avoid_scenes else "None",
                "breakdown": energy_breakdown
            }

        except Exception as e:
            flash(f"An error occurred: {e}", 'error')

    # This renders the page for GET requests and after the POST logic is complete
    return render_template_string(HTML_TEMPLATE, results=results)


if __name__ == '__main__':
    app.run(debug=True, port=5000)