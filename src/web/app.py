"""Flask web application for IGEL Profile Compare."""
import os
import sys
import uuid
import tempfile
from flask import Flask, render_template, request, jsonify, send_file, session

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ipm_handler import load_ipm
from core.comparator import compare_profiles
from core.migrator import migrate_settings

app = Flask(__name__, template_folder='../../templates', static_folder='../../static')
app.secret_key = 'igel-profile-compare-secret-key'

# Store uploaded profiles in memory
profiles = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload/<side>', methods=['POST'])
def upload(side):
    if side not in ('left', 'right'):
        return jsonify({'error': 'Invalid side'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.ipm'):
        return jsonify({'error': 'File must be .ipm'}), 400
    
    # Save to temp file
    temp_path = os.path.join(tempfile.gettempdir(), f'{uuid.uuid4()}.ipm')
    file.save(temp_path)
    
    try:
        profile = load_ipm(temp_path)
        profiles[side] = {'profile': profile, 'path': temp_path}
        flat = profile.get_flat_settings()
        return jsonify({
            'success': True,
            'name': profile.name,
            'settings_count': len(flat),
            'filename': file.filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/compare', methods=['POST'])
def compare():
    if 'left' not in profiles or 'right' not in profiles:
        return jsonify({'error': 'Please upload both profiles first'}), 400
    
    try:
        result = compare_profiles(profiles['left']['profile'], profiles['right']['profile'])
        
        # Format results for frontend
        data = {
            'left_name': result.left_name,
            'right_name': result.right_name,
            'summary': result.summary,
            'different': [{"key": k, "left": v[0]["value"], "right": v[1]["value"]} for k, v in sorted(result.different.items())],
            'only_left': [{"key": k, "value": v["value"]} for k, v in sorted(result.only_left.items())],
            'only_right': [{"key": k, "value": v["value"]} for k, v in sorted(result.only_right.items())],
            'identical': [{"key": k, "value": v["value"]} for k, v in sorted(result.identical.items())],
            'identical_count': len(result.identical)
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/migrate', methods=['POST'])
def migrate():
    if 'left' not in profiles or 'right' not in profiles:
        return jsonify({'error': 'Profiles not loaded'}), 400
    
    data = request.json
    keys = data.get('keys', [])
    
    if not keys:
        return jsonify({'error': 'No settings selected'}), 400
    
    try:
        output_path = os.path.join(tempfile.gettempdir(), f'migrated_{uuid.uuid4()}.ipm')
        migrate_settings(profiles['left']['profile'], profiles['right']['profile'], keys, output_path)
        
        return send_file(output_path, as_attachment=True, 
                        download_name=f"{profiles['right']['profile'].name}_migrated.ipm")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
