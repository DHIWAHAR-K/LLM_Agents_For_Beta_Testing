from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Replace with a strong secret key

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error loading template: {str(e)}"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and file.filename.endswith('.csv'):
        try:
            df = pd.read_csv(file)
            session['original_df'] = df.to_json()
            duplicates = df[df.duplicated(keep=False)]
            session['duplicates_df'] = duplicates.to_json()
            return render_template('results.html', original_data=df.to_html(), duplicate_data=duplicates.to_html())
        except Exception as e:
            return f"Error processing file: {e}"
    return "Invalid file type. Please upload a CSV."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

