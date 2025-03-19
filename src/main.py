from flask import Flask, request, jsonify, render_template, redirect, url_for
from google.cloud import bigquery

app = Flask(__name__, static_folder='../static', template_folder='../templates')
bigquery_client = bigquery.Client()

TABLE_ID = 'bdcp-201705314.bdcp.PATIENTS'

# Página principal
@app.route('/')
def index():
    return render_template('index.html')

# Adicionar Paciente (GET para carregar o formulário e POST para processar)
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        subject_id = request.form['subject_id']
        gender = request.form['gender']
        dob = request.form['dob']
        dod = request.form.get('dod', None)
        # Se dod estiver vazio, define como None (NULL)
        dod = dod if dod else None

        query = f"""
        INSERT INTO `{TABLE_ID}` (SUBJECT_ID, GENDER, DOB, DOD)
        VALUES (@subject_id, @gender, TIMESTAMP(@dob), TIMESTAMP(@dod))
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("subject_id", "INT64", subject_id),
                bigquery.ScalarQueryParameter("gender", "STRING", gender),
                bigquery.ScalarQueryParameter("dob", "DATE", dob),
                bigquery.ScalarQueryParameter("dod", "DATE", dod)
            ]
        )
        query_job = bigquery_client.query(query, job_config=job_config)
        query_job.result()

        return redirect(url_for('index'))
    return render_template('add_patient.html')

# Mostrar Pacientes
@app.route('/show_patients')
def show_patients():
    query = f"SELECT SUBJECT_ID, GENDER, DOB, DOD FROM `{TABLE_ID}`"
    query_job = bigquery_client.query(query)
    patients = query_job.result()
    return render_template('show_patients.html', patients=patients)

# Editar Paciente
@app.route('/edit_patient', methods=['GET', 'POST'])
def edit_patient():
    if request.method == 'POST':
        subject_id = request.form['subject_id']
        gender = request.form['gender']
        dob = request.form['dob']
        dod = request.form.get('dod', None)
        # Se dod estiver vazio, define como None (NULL)
        dod = dod if dod else None

        query = f"""
        UPDATE `{TABLE_ID}`
        SET GENDER = @gender, DOB = TIMESTAMP(@dob), DOD = TIMESTAMP(@dod)
        WHERE SUBJECT_ID = @subject_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("subject_id", "INT64", subject_id),
                bigquery.ScalarQueryParameter("gender", "STRING", gender),
                bigquery.ScalarQueryParameter("dob", "DATE", dob),
                bigquery.ScalarQueryParameter("dod", "DATE", dod)
            ]
        )
        query_job = bigquery_client.query(query, job_config=job_config)
        query_job.result()

        return redirect(url_for('index'))
    return render_template('edit_patient.html')

# Excluir Paciente
@app.route('/delete_patient', methods=['GET', 'POST'])
def delete_patient():
    if request.method == 'POST':
        subject_id = request.form['subject_id']

        query = f"DELETE FROM `{TABLE_ID}` WHERE SUBJECT_ID = @subject_id"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("subject_id", "INT64", subject_id)
            ]
        )
        query_job = bigquery_client.query(query, job_config=job_config)
        query_job.result()

        return redirect(url_for('index'))
    return render_template('delete_patient.html')

TABLE_QUESTIONS = 'bdcp-201705314.bdcp.QUESTIONS'

# Create a question for a specific patient
@app.route('/rest/patients/<int:patient_id>/question', methods=['POST'])
def create_question(patient_id):
    data = request.get_json()
    question_text = data.get('question_text')
    
    if not question_text:
        return jsonify({'error': 'Missing required fields'}), 400
    
    query = f'''
    INSERT INTO `{TABLE_QUESTIONS}` (PATIENT_ID, QUESTION_TEXT, ANSWER_TEXT)
    VALUES (@patient_id, @question_text, NULL)
    '''
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id),
            bigquery.ScalarQueryParameter("question_text", "STRING", question_text)
        ]
    )
    query_job = bigquery_client.query(query, job_config=job_config)
    query_job.result()
    
    return jsonify({'message': 'Question created successfully'}), 201

# Answer a question
@app.route('/rest/patients/<int:patient_id>/question/<int:question_id>', methods=['PUT'])
def answer_question(patient_id, question_id):
    data = request.get_json()
    answer_text = data.get('answer_text')
    
    if not answer_text:
        return jsonify({'error': 'Missing answer text'}), 400
    
    query = f'''
    UPDATE `{TABLE_QUESTIONS}`
    SET ANSWER_TEXT = @answer_text
    WHERE QUESTION_ID = @question_id AND PATIENT_ID = @patient_id
    '''
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("answer_text", "STRING", answer_text),
            bigquery.ScalarQueryParameter("question_id", "INT64", question_id),
            bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id)
        ]
    )
    query_job = bigquery_client.query(query, job_config=job_config)
    query_job.result()
    
    return jsonify({'message': 'Answer added successfully'}), 200

# List questions for a patient
@app.route('/rest/patients/<int:patient_id>/question', methods=['GET'])
def list_questions(patient_id):
    query = f'''
    SELECT QUESTION_ID, QUESTION_TEXT, ANSWER_TEXT 
    FROM `{TABLE_QUESTIONS}`
    WHERE PATIENT_ID = @patient_id
    '''
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id)
        ]
    )
    query_job = bigquery_client.query(query, job_config=job_config)
    results = query_job.result()
    
    questions = [
        {
            'question_id': row.QUESTION_ID,
            'question_text': row.QUESTION_TEXT,
            'answer_text': row.ANSWER_TEXT
        } for row in results
    ]
    
    return jsonify({'questions': questions}), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
