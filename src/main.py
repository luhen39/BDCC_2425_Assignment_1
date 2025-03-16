from flask import Flask, request, jsonify, render_template, redirect, url_for
from google.cloud import bigquery
from datetime import datetime

app = Flask(__name__, static_folder='../static', template_folder='../templates')
bigquery_client = bigquery.Client()

# Constants
PATIENTS_TABLE = 'bdcp-201705314.bdcp.PATIENTS'
ADMISSIONS_TABLE = 'bdcp-201705314.bdcp.ADMISSIONS'
INPUTEVENTS_TABLE = 'bdcp-201705314.bdcp.INPUTEVENTS'
LABEVENTS_TABLE = 'bdcp-201705314.bdcp.LABEVENTS'
DELETED_USER_ID = -1  # ID for the "Deleted User"

# Ensure the "Deleted User" exists in the PATIENTS table
def ensure_deleted_user_exists():
    try:
        query = f"""
        SELECT SUBJECT_ID FROM `{PATIENTS_TABLE}` WHERE SUBJECT_ID = @deleted_user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("deleted_user_id", "INT64", DELETED_USER_ID)
            ]
        )
        query_job = bigquery_client.query(query, job_config=job_config)
        result = query_job.result()

        if not list(result):
            # If the "Deleted User" does not exist, create it
            query = f"""
            INSERT INTO `{PATIENTS_TABLE}` (SUBJECT_ID, GENDER, DOB, DOD)
            VALUES (@deleted_user_id, 'Unknown', '1900-01-01', NULL)
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("deleted_user_id", "INT64", DELETED_USER_ID)
                ]
            )
            query_job = bigquery_client.query(query, job_config=job_config)
            query_job.result()
    except Exception as e:
        print(f"Error ensuring 'Deleted User' exists: {e}")

# Validate patient data
def validate_patient_data(data):
    if not data.get('subject_id'):
        raise ValueError("subject_id is required")
    if not isinstance(data['subject_id'], int):
        raise ValueError("subject_id must be an integer")
    if not data.get('gender'):
        raise ValueError("gender is required")
    if not data.get('dob'):
        raise ValueError("date of birth (dob) is required")

# Página principal
@app.route('/')
def index():
    return render_template('index.html')

# Adicionar Paciente (GET para carregar o formulário e POST para processar)
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        try:
            # Extract and validate form data
            subject_id = int(request.form['subject_id'])
            gender = request.form['gender']
            dob = request.form['dob']
            dod = request.form.get('dod', None)
            dod = dod if dod else None

            # Validate patient data
            validate_patient_data({
                'subject_id': subject_id,
                'gender': gender,
                'dob': dob
            })

            # Insert patient into the database
            query = f"""
            INSERT INTO `{PATIENTS_TABLE}` (SUBJECT_ID, GENDER, DOB, DOD)
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
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return render_template('add_patient.html')

# Mostrar Pacientes
@app.route('/show_patients')
def show_patients():
    try:
        query = f"SELECT SUBJECT_ID, GENDER, DOB, DOD FROM `{PATIENTS_TABLE}`"
        query_job = bigquery_client.query(query)
        patients = query_job.result()
        return render_template('show_patients.html', patients=patients)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar Paciente
@app.route('/edit_patient', methods=['GET', 'POST'])
def edit_patient():
    if request.method == 'POST':
        try:
            # Extract and validate form data
            subject_id = int(request.form['subject_id'])
            gender = request.form['gender']
            dob = request.form['dob']
            dod = request.form.get('dod', None)
            dod = dod if dod else None

            # Validate patient data
            validate_patient_data({
                'subject_id': subject_id,
                'gender': gender,
                'dob': dob
            })

            # Update patient in the database
            query = f"""
            UPDATE `{PATIENTS_TABLE}`
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
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return render_template('edit_patient.html')

# Delete Patient and Update Admissions and Progress
@app.route('/delete_patient', methods=['GET', 'POST'])
def delete_patient():
    if request.method == 'POST':
        try:
            # Get the patient ID from the form
            subject_id = int(request.form['subject_id'])

            # Ensure the "Deleted User" exists in the PATIENTS table
            ensure_deleted_user_exists()

            # Update related tables to set SUBJECT_ID to DELETED_USER_ID (-1)
            update_queries = [
                (f"UPDATE `{ADMISSIONS_TABLE}` SET SUBJECT_ID = @deleted_user_id WHERE SUBJECT_ID = @subject_id", "ADMISSIONS"),
                (f"UPDATE `{INPUTEVENTS_TABLE}` SET SUBJECT_ID = @deleted_user_id WHERE SUBJECT_ID = @subject_id", "INPUTEVENTS"),
                (f"UPDATE `{LABEVENTS_TABLE}` SET SUBJECT_ID = @deleted_user_id WHERE SUBJECT_ID = @subject_id", "LABEVENTS")
            ]
            for query, table in update_queries:
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("deleted_user_id", "INT64", DELETED_USER_ID),
                        bigquery.ScalarQueryParameter("subject_id", "INT64", subject_id)
                    ]
                )
                query_job = bigquery_client.query(query, job_config=job_config)
                query_job.result()

            # Delete the patient from the PATIENTS table
            delete_patient_query = f"""
            DELETE FROM `{PATIENTS_TABLE}`
            WHERE SUBJECT_ID = @subject_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("subject_id", "INT64", subject_id)
                ]
            )
            query_job = bigquery_client.query(delete_patient_query, job_config=job_config)
            query_job.result()

            return redirect(url_for('index'))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return render_template('delete_patient.html')


# Show Admissions
@app.route('/show_admissions')
def show_admissions():
    try:
        patient_id = request.args.get('patient_id')
        if not patient_id:
            return jsonify({"error": "patient_id is required"}), 400
        patient_id = int(patient_id)

        # Check if the patient exists in the PATIENTS table
        patient_exists_query = f"""
        SELECT SUBJECT_ID FROM `{PATIENTS_TABLE}` WHERE SUBJECT_ID = @patient_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id)
            ]
        )
        patient_exists_job = bigquery_client.query(patient_exists_query, job_config=job_config)
        patient_exists = list(patient_exists_job.result())

        if not patient_exists:
            # If the patient has been deleted, use DELETED_USER_ID
            patient_id = DELETED_USER_ID

        query = f"""
        SELECT HADM_ID, ADMITTIME, DISCHTIME, ADMISSION_TYPE, DIAGNOSIS, SUBJECT_ID
        FROM `{ADMISSIONS_TABLE}`
        WHERE SUBJECT_ID = @patient_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id)
            ]
        )
        query_job = bigquery_client.query(query, job_config=job_config)
        admissions = query_job.result()

        return render_template('show_admissions.html', admissions=admissions, patient_id=patient_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Helper function to convert datetime-local to BigQuery timestamp
def convert_to_bigquery_timestamp(datetime_str):
    if datetime_str:
        # Replace 'T' with a space and append ':00' if seconds are missing
        datetime_str = datetime_str.replace('T', ' ') + ':00'
        return datetime_str
    return None

# Add Admission (GET for form, POST for processing)
# Add Admission (GET for form, POST for processing)
@app.route('/add_admission', methods=['GET', 'POST'])
def add_admission():
    if request.method == 'POST':
        try:
            # Extract form data
            patient_id = int(request.form['patient_id'])
            admission_time = convert_to_bigquery_timestamp(request.form['admission_time'])
            discharge_time = convert_to_bigquery_timestamp(request.form.get('discharge_time', None))
            admission_type = request.form.get('admission_type', None)
            diagnosis = request.form.get('diagnosis', None)

            # Generate a unique HADM_ID
            query = f"""
            SELECT MAX(HADM_ID) as max_id FROM `{ADMISSIONS_TABLE}`
            """
            query_job = bigquery_client.query(query)
            result = list(query_job.result())  # Convert the RowIterator to a list
            max_id = result[0].max_id if result[0].max_id else 0  # Get the maximum ID or default to 0
            new_admission_id = max_id + 1  # Increment the maximum ID by 1

            # Insert admission into the database
            query = f"""
            INSERT INTO `{ADMISSIONS_TABLE}` (HADM_ID, SUBJECT_ID, ADMITTIME, DISCHTIME, ADMISSION_TYPE, DIAGNOSIS)
            VALUES (@hadm_id, @patient_id, TIMESTAMP(@admission_time), TIMESTAMP(@discharge_time), @admission_type, @diagnosis)
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("hadm_id", "INT64", new_admission_id),
                    bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id),
                    bigquery.ScalarQueryParameter("admission_time", "TIMESTAMP", admission_time),
                    bigquery.ScalarQueryParameter("discharge_time", "TIMESTAMP", discharge_time),
                    bigquery.ScalarQueryParameter("admission_type", "STRING", admission_type),
                    bigquery.ScalarQueryParameter("diagnosis", "STRING", diagnosis)
                ]
            )
            query_job = bigquery_client.query(query, job_config=job_config)
            query_job.result()

            return redirect(url_for('show_admissions', patient_id=patient_id))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # Pre-fill the patient ID if provided in the query parameters
        patient_id = request.args.get('patient_id')
        return render_template('add_admission.html', patient_id=patient_id)

# Edit Admission (GET for form, POST for processing)
@app.route('/edit_admission/<int:admission_id>', methods=['GET', 'POST'])
def edit_admission(admission_id):
    if request.method == 'POST':
        try:
            # Extract form data
            patient_id = int(request.form['patient_id'])
            admission_time = convert_to_bigquery_timestamp(request.form.get('admission_time', None))
            discharge_time = convert_to_bigquery_timestamp(request.form.get('discharge_time', None))
            admission_type = request.form.get('admission_type', None)
            diagnosis = request.form.get('diagnosis', None)

            # Build the update query dynamically based on provided fields
            update_fields = []
            query_parameters = [
                bigquery.ScalarQueryParameter("admission_id", "INT64", admission_id)
            ]

            if admission_time:
                update_fields.append("ADMITTIME = TIMESTAMP(@admission_time)")
                query_parameters.append(bigquery.ScalarQueryParameter("admission_time", "TIMESTAMP", admission_time))
            if discharge_time:
                update_fields.append("DISCHTIME = TIMESTAMP(@discharge_time)")
                query_parameters.append(bigquery.ScalarQueryParameter("discharge_time", "TIMESTAMP", discharge_time))
            if admission_type:
                update_fields.append("ADMISSION_TYPE = @admission_type")
                query_parameters.append(bigquery.ScalarQueryParameter("admission_type", "STRING", admission_type))
            if diagnosis:
                update_fields.append("DIAGNOSIS = @diagnosis")
                query_parameters.append(bigquery.ScalarQueryParameter("diagnosis", "STRING", diagnosis))

            if not update_fields:
                return jsonify({"error": "No fields provided for update"}), 400

            # Construct the update query
            query = f"""
            UPDATE `{ADMISSIONS_TABLE}`
            SET {', '.join(update_fields)}
            WHERE HADM_ID = @admission_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=query_parameters
            )
            query_job = bigquery_client.query(query, job_config=job_config)
            query_job.result()

            return redirect(url_for('show_admissions', patient_id=patient_id))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # Fetch the admission details to pre-fill the form
        try:
            query = f"""
            SELECT HADM_ID, SUBJECT_ID, ADMITTIME, DISCHTIME, ADMISSION_TYPE, DIAGNOSIS
            FROM `{ADMISSIONS_TABLE}`
            WHERE HADM_ID = @admission_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("admission_id", "INT64", admission_id)
                ]
            )
            query_job = bigquery_client.query(query, job_config=job_config)
            admission = list(query_job.result())[0]  # Get the first (and only) result

            return render_template('edit_admission.html', admission=admission)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Show Progress (Input Events and Lab Events)
@app.route('/show_progress')
def show_progress():
    try:
        patient_id = request.args.get('patient_id')
        if not patient_id:
            return jsonify({"error": "patient_id is required"}), 400

        patient_id = int(patient_id)

        # 1) Check if the patient exists
        check_query = f"""
        SELECT SUBJECT_ID
        FROM `{PATIENTS_TABLE}`
        WHERE SUBJECT_ID = @patient_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id)
            ]
        )
        query_job = bigquery_client.query(check_query, job_config=job_config)
        results = list(query_job.result())

        # 2) If the patient doesn't exist, use DELETED_USER_ID
        if not results:
            patient_id = DELETED_USER_ID  # -1

        # Fetch input events
        input_events_query = f"""
        SELECT CHARTTIME, ITEMID, AMOUNT, RATE, SUBJECT_ID
        FROM `{INPUTEVENTS_TABLE}`
        WHERE SUBJECT_ID = @patient_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id)
            ]
        )
        input_events_job = bigquery_client.query(input_events_query, job_config=job_config)
        input_events = [dict(row) for row in input_events_job.result()]

        # Fetch lab events
        lab_events_query = f"""
        SELECT CHARTTIME, ITEMID, VALUE, VALUENUM, FLAG, SUBJECT_ID
        FROM `{LABEVENTS_TABLE}`
        WHERE SUBJECT_ID = @patient_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id)
            ]
        )
        lab_events_job = bigquery_client.query(lab_events_query, job_config=job_config)
        lab_events = [dict(row) for row in lab_events_job.result()]

        progress_data = {
            "input_events": input_events,
            "lab_events": lab_events
        }

        # Pass patient_id (which might now be -1) to the template
        return render_template('show_progress.html',
                               progress_data=progress_data,
                               patient_id=patient_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Ensure the "Deleted User" exists when the application starts
    ensure_deleted_user_exists()
    app.run(host='127.0.0.1', port=8080, debug=True)