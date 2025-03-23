from flask import Flask, request, Request, jsonify, render_template, redirect, url_for
from google.cloud import bigquery,storage
from datetime import datetime
import logging
import functions_framework # type: ignore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../static', template_folder='../templates')
bigquery_client = bigquery.Client()
storage_client = storage.Client()

# Constants
PATIENTS_TABLE = 'bdcp-201705314.bdcp.PATIENTS'
ADMISSIONS_TABLE = 'bdcp-201705314.bdcp.ADMISSIONS'
ADMISSION_TRENDS_TABLE = 'bdcp-201705314.bdcp.ADMISSION_TRENDS'
INPUTEVENTS_TABLE = 'bdcp-201705314.bdcp.INPUTEVENTS'
LABEVENTS_TABLE = 'bdcp-201705314.bdcp.LABEVENTS'
LAB_ANOMALIES_TABLE = 'bdcp-201705314.bdcp.LAB_ANOMALIES'
QUESTIONS_TABLE = 'bdcp-201705314.bdcp.QUESTIONS'
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
    
# Cloud Function to update the LONG_WAITING_TIMES table
@functions_framework.http  # This makes it an HTTP-triggered function
def update_long_waiting(request: Request):
    """Cloud Function to update the LONG_WAITING_TIMES table."""
    client = bigquery.Client()
    target_table = "bdcp-201705314.bdcp.LONG_WAITING_TIMES"

    try:
        # Check if the table exists, and create it if it doesn't
        try:
            client.get_table(target_table)  # Check if table exists
        except Exception:
            schema = [
                bigquery.SchemaField("PATIENT_ID", "INT64", mode="REQUIRED"),
                bigquery.SchemaField("HADM_ID", "INT64", mode="REQUIRED"),
                bigquery.SchemaField("ADMITTIME", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("DISCHTIME", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("WAITING_TIME_HOURS", "INT64", mode="REQUIRED"),
                bigquery.SchemaField("LAST_UPDATED", "TIMESTAMP", mode="REQUIRED"),
            ]
            table = bigquery.Table(target_table, schema=schema)
            client.create_table(table)
            logger.info(f"Created table {target_table}")

        # Query to get long waiting patients
        query = """
            WITH AdmissionData AS (
                SELECT
                    SUBJECT_ID AS PATIENT_ID,
                    HADM_ID,
                    ADMITTIME,
                    DISCHTIME,
                    TIMESTAMP_DIFF(
                        IFNULL(DISCHTIME, CURRENT_TIMESTAMP()), 
                        ADMITTIME, 
                        HOUR
                    ) AS WAITING_TIME_HOURS,
                    CURRENT_TIMESTAMP() AS LAST_UPDATED
                FROM `bdcp-201705314.bdcp.ADMISSIONS`
                WHERE SUBJECT_ID > 0
            )
            SELECT *
            FROM AdmissionData
            ORDER BY WAITING_TIME_HOURS DESC
            LIMIT 10
        """

        # Configure query job
        job_config = bigquery.QueryJobConfig(
            destination=target_table,
            write_disposition="WRITE_TRUNCATE"
        )

        # Execute query
        query_job = client.query(query, job_config=job_config)
        query_job.result()

        logger.info(f"Updated long waiting times in {target_table}")
        return jsonify({"message": f"Updated long waiting times in {target_table}"}), 200

    except Exception as e:
        logger.error(f"Error in update_long_waiting: {e}")
        return jsonify({"error": str(e)}), 500

# Página principal
@app.route('/')
def index():
    return render_template('index.html')

############ Patient Management System ###########################

# Adicionar Paciente (GET para carregar o formulário e POST para processar)
@app.route('/pms/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        try:
            # Generate a unique HADM_ID
            query = f"""
            SELECT MAX(SUBJECT_ID) as max_id FROM `{PATIENTS_TABLE}`
            """
            query_job = bigquery_client.query(query)
            result = list(query_job.result())  # Convert the RowIterator to a list
            max_id = result[0].max_id if result[0].max_id else 0  # Get the maximum ID or default to 0
            subject_id = max_id + 1  # Increment the maximum ID by 1

            # Extract and validate form data
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
    return render_template('/pms/add_patient.html')

# Mostrar Pacientes
@app.route('/pms/show_patients')
def show_patients():
    try:
        query = f"SELECT SUBJECT_ID, GENDER, DOB, DOD FROM `{PATIENTS_TABLE}`"
        query_job = bigquery_client.query(query)
        patients = query_job.result()
        return render_template('/pms/show_patients.html', patients=patients)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar Paciente
@app.route('/pms/edit_patient/<int:subject_id>', methods=['GET', 'POST'])
def edit_patient(subject_id):
    if request.method == 'POST':
        try:
            # Extract and validate form data
            gender = request.form['gender']
            dob = request.form['dob']
            dod = request.form.get('dod', None)
            dod = dod if dod else None
            media_keys = request.form.getlist('media_keys')  # Get media keys from form

            # Validate patient data
            validate_patient_data({
                'subject_id': subject_id,
                'gender': gender,
                'dob': dob
            })

            # Update patient in the database
            query = f"""
            UPDATE `{PATIENTS_TABLE}`
            SET GENDER = @gender, DOB = TIMESTAMP(@dob), DOD = TIMESTAMP(@dod), Media_Key_Array = @media_keys
            WHERE SUBJECT_ID = @subject_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("subject_id", "INT64", subject_id),
                    bigquery.ScalarQueryParameter("gender", "STRING", gender),
                    bigquery.ScalarQueryParameter("dob", "DATE", dob),
                    bigquery.ScalarQueryParameter("dod", "DATE", dod),
                    bigquery.ArrayQueryParameter("media_keys", "STRING", media_keys)
                ]
            )
            query_job = bigquery_client.query(query, job_config=job_config)
            query_job.result()

            return redirect(url_for('index'))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return render_template('/pms/edit_patient.html', subject_id=subject_id)

# Delete Patient and Update Admissions and Progress
@app.route('/pms/delete_patient', methods=['GET', 'POST'])
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
    return render_template('/pms/delete_patient.html')


# Show Admissions
@app.route('/pms/show_admissions')
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

        return render_template('/pms/show_admissions.html', admissions=admissions, patient_id=patient_id)
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
@app.route('/pms/add_admission', methods=['GET', 'POST'])
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
        return render_template('/pms/add_admission.html', patient_id=patient_id)

# Edit Admission (GET for form, POST for processing)
@app.route('/pms/edit_admission/<int:admission_id>', methods=['GET', 'POST'])
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

            return render_template('/pms/edit_admission.html', admission=admission)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@functions_framework.http
def analyze_admission_trends(request):
    """Cloud Function to analyze admission trends and store results."""
    client = bigquery.Client()

    try:
        # Check if the ADMISSION_TRENDS table exists, and create it if it doesn't
        try:
            client.get_table(ADMISSION_TRENDS_TABLE)
        except Exception:
            schema = [
                bigquery.SchemaField("MONTH", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("YEAR", "INT64", mode="REQUIRED"),
                bigquery.SchemaField("ADMISSION_COUNT", "INT64", mode="REQUIRED"),
                bigquery.SchemaField("AVG_LENGTH_OF_STAY_HOURS", "FLOAT64", mode="REQUIRED"),
                bigquery.SchemaField("PEAK_ADMISSION_DAY", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("LAST_UPDATED", "TIMESTAMP", mode="REQUIRED"),
            ]
            table = bigquery.Table(ADMISSION_TRENDS_TABLE, schema=schema)
            client.create_table(table)
            logger.info(f"Created table {ADMISSION_TRENDS_TABLE}")

        # Corrected query
        query = """
        WITH AdmissionData AS (
            SELECT
                FORMAT_TIMESTAMP('%Y-%m', ADMITTIME) AS MONTH_YEAR,
                EXTRACT(YEAR FROM ADMITTIME) AS YEAR,
                EXTRACT(MONTH FROM ADMITTIME) AS MONTH,
                ADMITTIME,
                DISCHTIME,
                TIMESTAMP_DIFF(IFNULL(DISCHTIME, CURRENT_TIMESTAMP()), ADMITTIME, HOUR) AS LENGTH_OF_STAY_HOURS,
                FORMAT_TIMESTAMP('%A', ADMITTIME) AS ADMISSION_DAY
            FROM `bdcp-201705314.bdcp.ADMISSIONS`
        ),
        AdmissionDayCounts AS (
            SELECT
                YEAR,
                MONTH,
                ADMISSION_DAY,
                COUNT(*) AS DAY_COUNT
            FROM AdmissionData
            GROUP BY YEAR, MONTH, ADMISSION_DAY
        ),
        PeakAdmissionDay AS (
            SELECT
                YEAR,
                MONTH,
                ARRAY_AGG(ADMISSION_DAY ORDER BY DAY_COUNT DESC LIMIT 1)[OFFSET(0)] AS PEAK_ADMISSION_DAY
            FROM AdmissionDayCounts
            GROUP BY YEAR, MONTH
        )
        SELECT
            CONCAT(CAST(YEAR AS STRING), '-', LPAD(CAST(MONTH AS STRING), 2, '0')) AS MONTH,
            YEAR,
            COUNT(*) AS ADMISSION_COUNT,
            AVG(LENGTH_OF_STAY_HOURS) AS AVG_LENGTH_OF_STAY_HOURS,
            PEAK_ADMISSION_DAY,
            CURRENT_TIMESTAMP() AS LAST_UPDATED
        FROM AdmissionData
        JOIN PeakAdmissionDay USING (YEAR, MONTH)
        GROUP BY YEAR, MONTH, PEAK_ADMISSION_DAY
        ORDER BY YEAR, MONTH
        """

        # Configure query job to write results to ADMISSION_TRENDS table
        job_config = bigquery.QueryJobConfig(
            destination=ADMISSION_TRENDS_TABLE,
            write_disposition="WRITE_TRUNCATE"
        )

        # Execute query
        query_job = client.query(query, job_config=job_config)
        query_job.result()

        logger.info(f"Updated admission trends in {ADMISSION_TRENDS_TABLE}")
        return jsonify({"message": f"Updated admission trends in {ADMISSION_TRENDS_TABLE}"}), 200

    except Exception as e:
        logger.error(f"Error in analyze_admission_trends: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/pms/admission_trends')
def show_admission_trends():
    try:
        # Query the ADMISSION_TRENDS table
        query = f"""
        SELECT MONTH, YEAR, ADMISSION_COUNT, AVG_LENGTH_OF_STAY_HOURS, PEAK_ADMISSION_DAY
        FROM `{ADMISSION_TRENDS_TABLE}`
        ORDER BY YEAR DESC, MONTH DESC
        """
        query_job = bigquery_client.query(query)
        trends = [dict(row) for row in query_job.result()]

        # Render the results in an HTML template
        return render_template('/pms/admission_trends.html', trends=trends)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Show Progress (Input Events and Lab Events)
@app.route('/pms/show_progress')
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
        return render_template('/pms/show_progress.html',
                               progress_data=progress_data,
                               patient_id=patient_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
############ Media Management System ###########################

bucket_name = 'patient_media_bucket'

def get_or_create_bucket(bucket_name):
    """Verifica se o bucket existe; caso contrário, cria um."""
    bucket = storage_client.bucket(bucket_name)
    
    if not bucket.exists():
        bucket = storage_client.create_bucket(bucket_name, location="US")
        print(f"Bucket {bucket_name} created.")
    else:
        print(f"Bucket {bucket_name} already exists.")
    
    return bucket

### 1. Adicionar Mídia ### OK

@app.route("/mms/upload_media", methods=["GET", "POST"])
def upload_media():
    """Carrega mídia para o GCS. Pode ou não associar ao paciente."""
    if request.method == "POST":
        # Verifica se há um arquivo no formulário
        if 'file' not in request.files:
            return "No file provided", 400

        photo = request.files['file']
        subject_id = request.form.get('subject_id')  # O subject_id pode estar vazio

        if photo.filename == '':
            return "No selected file", 400

        # Verifica se o bucket existe ou cria um novo
        bucket = get_or_create_bucket(bucket_name)

        # Cria um blob no bucket para o arquivo 
        blob = bucket.blob(photo.filename)  
        blob.content_type = "application/octet-stream"

        # Faz o upload do arquivo para o bucket
        blob.upload_from_file(photo)

        # Opcional: Torna o arquivo público (pode ser removido se quiser URLs assinadas)
        blob.make_public()

        # Obtém o Blob hash para usar como chave da mídia
        media_key = blob.id

        # Verifica se foi fornecido um `subject_id` para associar ao paciente
        if subject_id:
            subject_id = int(subject_id)  # Converte para INT se houver um ID

            # Consulta para obter o array atual de Media_Key_Array
            query_get_array = f"""
                SELECT Media_Key_Array
                FROM `{PATIENTS_TABLE}`
                WHERE SUBJECT_ID = @subject_id
            """
            # Executa a consulta para obter o array atual
            query_job = bigquery_client.query(query_get_array, job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("subject_id", "INT64", subject_id)]
            ))

            # Recupera os resultados
            result = query_job.result()
            row = next(result, None)

            # Se o array de Media_Key_Array existir, caso contrário, inicia com array vazio
            if row and row.Media_Key_Array:
                media_key_array = row.Media_Key_Array
            else:
                media_key_array = []

            # Adiciona a nova media_key ao array
            media_key_array.append(media_key)

            # Query de UPDATE para adicionar a nova media_key ao array
            query_update = f"""
                UPDATE `{PATIENTS_TABLE}`
                SET Media_Key_Array = @media_key_array
                WHERE SUBJECT_ID = @subject_id
            """
            
            # Configura os parâmetros para a query de UPDATE no BigQuery
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("media_key_array", "STRING", media_key_array),
                    bigquery.ScalarQueryParameter("subject_id", "INT64", subject_id)
                ]
            )

            # Executa a query de UPDATE
            query_job = bigquery_client.query(query_update, job_config=job_config)
            query_job.result()  # Aguarda o término da execução da query

            return f"""
                <html>
                    <body>
                        <p>Media uploaded successfully and associated with patient {subject_id}</p>
                        <button onclick="location.href='/'">Back to Main Page</button>
                    </body>
                </html>
                """
        else:
            # Se não há `subject_id`, apenas faz o upload da mídia
            return """
                <html>
                    <body>
                        <p>Media uploaded successfully without association to a patient</p>
                        <button onclick="location.href='/'">Back to Main Page</button>
                    </body>
                </html>
                """

    # GET method: Renderiza o template para adicionar mídia
    return render_template("mms/upload_media.html")

### 2. Download Mídia na Cloud Storage ###
@app.route("/mms/download_media", methods=["GET", "POST"])
def download_media_form():
    """Formulário para inserir o ID da mídia e visualizar."""
    return render_template("mms/download_media.html")

@app.route("/mms/download_media/<media_key>")
def donwload_media(media_key):
    """Inicia download da mídia armazenada no Google Cloud Storage."""
    bucket = get_or_create_bucket(bucket_name)
    blob = bucket.get_blob(media_key)

    if not blob:
        return "Media not found", 404

    # Redireciona para a URL pública do arquivo
    return redirect(blob.public_url)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

### 4. Exibir a Mídias ###

@app.route("/mms/show_media", methods=["GET", "POST"])
def show_media_form():
    """Formulário para inserir o ID da mídia e visualizar."""
    return render_template("mms/show_media.html")

@app.route("/mms/show_media/<media_key>")
def view_media(media_key):
    """Redireciona para a visualização da mídia armazenada no Google Cloud Storage."""
    bucket = get_or_create_bucket(bucket_name)
    blob = bucket.get_blob(media_key)

    if not blob:
        return "Media not found", 404

    # Renderiza o template com a URL da mídia
    return render_template("mms/show_media.html", media_url=blob.public_url)


# Questions Section
@app.route('/qms/questions')
def questions_section():
    return render_template('/qms/questions.html')

# Ask a Question (from us to a patient)
@app.route('/qms/ask_question', methods=['GET', 'POST'])
def ask_question():
    if request.method == 'POST':
        try:
            # Extract form data
            patient_id = int(request.form['patient_id'])
            question_text = request.form['question_text']

            # Generate a unique QUESTION_ID
            query = f"""
            SELECT MAX(QUESTION_ID) as max_id FROM `{QUESTIONS_TABLE}`
            """
            query_job = bigquery_client.query(query)
            result = list(query_job.result())
            max_id = result[0].max_id if result[0].max_id else 0
            new_question_id = max_id + 1

            # Insert the question into the database (source: STAFF)
            query = f"""
            INSERT INTO `{QUESTIONS_TABLE}` (QUESTION_ID, PATIENT_ID, QUESTION_TEXT, CREATED_AT, QUESTION_SOURCE)
            VALUES (@question_id, @patient_id, @question_text, CURRENT_TIMESTAMP(), @question_source)
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("question_id", "INT64", new_question_id),
                    bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id),
                    bigquery.ScalarQueryParameter("question_text", "STRING", question_text),
                    bigquery.ScalarQueryParameter("question_source", "STRING", "STAFF")
                ]
            )
            query_job = bigquery_client.query(query, job_config=job_config)
            query_job.result()

            return redirect(url_for('view_questions', patient_id=patient_id))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return render_template('/qms/ask_question.html')

# View Questions for a Patient
@app.route('/qms/view_questions', methods=['GET'])
def view_questions():
    try:
        patient_id = request.args.get('patient_id')
        if not patient_id:
            return jsonify({"error": "patient_id is required"}), 400

        patient_id = int(patient_id)

        # Fetch all questions for the patient
        query = f"""
        SELECT QUESTION_ID, PATIENT_ID, QUESTION_TEXT, ANSWER_TEXT, CREATED_AT, QUESTION_SOURCE
        FROM `{QUESTIONS_TABLE}`
        WHERE PATIENT_ID = @patient_id
        ORDER BY CREATED_AT DESC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id)
            ]
        )
        query_job = bigquery_client.query(query, job_config=job_config)
        questions = [dict(row) for row in query_job.result()]

        # If no questions are found, return a message
        if not questions:
            return render_template('/qms/view_questions.html', no_questions=True, patient_id=patient_id)

        return render_template('/qms/view_questions.html', questions=questions, patient_id=patient_id, no_questions=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Reply to a Question (only for questions from patients)
@app.route('/qms/reply_question', methods=['POST'])
def reply_question():
    try:
        # Extract form data
        parent_question_id = int(request.form['parent_question_id'])
        patient_id = int(request.form['patient_id'])
        reply_text = request.form['reply_text']
        question_source = request.form.get('question_source', 'STAFF')  # Default to STAFF if not provided

        # Generate a unique QUESTION_ID
        query = f"""
        SELECT MAX(QUESTION_ID) as max_id FROM `{QUESTIONS_TABLE}`
        """
        query_job = bigquery_client.query(query)
        result = list(query_job.result())
        max_id = result[0].max_id if result[0].max_id else 0
        new_question_id = max_id + 1

        # Insert the reply into the database
        query = f"""
        INSERT INTO `{QUESTIONS_TABLE}` (QUESTION_ID, PATIENT_ID, QUESTION_TEXT, CREATED_AT, QUESTION_SOURCE, PARENT_QUESTION_ID)
        VALUES (@question_id, @patient_id, @reply_text, CURRENT_TIMESTAMP(), @question_source, @parent_question_id)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("question_id", "INT64", new_question_id),
                bigquery.ScalarQueryParameter("patient_id", "INT64", patient_id),
                bigquery.ScalarQueryParameter("reply_text", "STRING", reply_text),
                bigquery.ScalarQueryParameter("question_source", "STRING", question_source),
                bigquery.ScalarQueryParameter("parent_question_id", "INT64", parent_question_id)
            ]
        )
        query_job = bigquery_client.query(query, job_config=job_config)
        query_job.result()

        return redirect(url_for('view_questions', patient_id=patient_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/pms/longer_waiting_time')
def long_waiting_patients():
    try:
        query = """
            SELECT *
            FROM `bdcp-201705314.bdcp.LONG_WAITING_TIMES`
            ORDER BY WAITING_TIME_HOURS DESC
        """
        query_job = bigquery_client.query(query)
        waiting_patients = [dict(row) for row in query_job.result()]
        
        if not waiting_patients:
            return render_template('pms/longer_waiting_time.html', waiting_patients=[], message="No data available")
            
        return render_template('pms/longer_waiting_time.html', waiting_patients=waiting_patients)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Ensure the "Deleted User" exists when the application starts
    ensure_deleted_user_exists()
    app.run(host='127.0.0.1', port=8080, debug=True)