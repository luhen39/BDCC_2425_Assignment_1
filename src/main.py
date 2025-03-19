from flask import Flask, request, jsonify, render_template, redirect, url_for
from google.cloud import bigquery,storage

app = Flask(__name__, static_folder='../static', template_folder='../templates')
bigquery_client = bigquery.Client()
storage_client = storage.Client()

# Página principal
@app.route('/')
def index():
    return render_template('index.html')

############ Patient Management System ###########################

TABLE_ID = 'bdcp-201705314.bdcp.PATIENTS'

# Adicionar Paciente (GET para carregar o formulário e POST para processar)
@app.route('/pms/add_patient', methods=['GET', 'POST'])
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
    return render_template('pms/add_patient.html')

# Mostrar Pacientes
@app.route('/pms/show_patients')
def show_patients():
    query = f"SELECT SUBJECT_ID, GENDER, DOB, DOD FROM `{TABLE_ID}`"
    query_job = bigquery_client.query(query)
    patients = query_job.result()
    return render_template('pms/show_patients.html', patients=patients)

# Editar Paciente
@app.route('/pms/edit_patient', methods=['GET', 'POST'])
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
    return render_template('pms/edit_patient.html')

# Excluir Paciente
@app.route('/pms/delete_patient', methods=['GET', 'POST'])
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
    
    return render_template('pms/delete_patient.html')

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


### 1. Adicionar Mídia ###

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

        # Obtém o Blob ID para usar como chave da mídia
        media_key = blob.id

        # Verifica se foi fornecido um `subject_id` para associar ao paciente
        if subject_id:
            subject_id = int(subject_id)  # Converte para INT se houver um ID

            # Consulta para obter o array atual de Media_Key_Array
            query_get_array = f"""
                SELECT Media_Key_Array
                FROM `{TABLE_ID}`
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
                UPDATE `{TABLE_ID}`
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

@app.route("/mms/download_media", methods=["GET", "POST"])
def download_media_interface():
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

        # Faz o upload do arquivo para o bucket
        blob.upload_from_file(photo)

        # Opcional: Torna o arquivo público (pode ser removido se quiser URLs assinadas)
        blob.make_public()

        # Obtém o Blob ID para usar como chave da mídia
        media_key = blob.id

        # Verifica se foi fornecido um `subject_id` para associar ao paciente
        if subject_id:
            subject_id = int(subject_id)  # Converte para INT se houver um ID

            # Consulta para obter o array atual de Media_Key_Array
            query_get_array = f"""
                SELECT Media_Key_Array
                FROM `{TABLE_ID}`
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
                UPDATE `{TABLE_ID}`
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
    return render_template("mms/download_media.html")

### 3. Visualizar Mídia na Cloud Storage ###

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

### 2. Exibir a Lista de Mídias de um Paciente ###

@app.route("/mms/<patient_id>")
def list_patient_media(patient_id):
    """Lista todos os detalhes das mídias associadas a um paciente, com links clicáveis para visualização."""
    
    # Recupera a lista de chaves de mídia do paciente no BigQuery
    query = f"""
    SELECT Media_Key
    FROM `{TABLE_ID}`
    WHERE SUBJECT_ID = @subject_id
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("subject_id", "INT64", int(patient_id))
        ]
    )

    query_job = bigquery_client.query(query, job_config=job_config)
    result = query_job.result()

    # Verifica se o paciente tem mídia associada
    media_keys = None
    for row in result:
        media_keys = row['Media_Key']

    if not media_keys:
        return jsonify({"message": "No media associated with this patient."}), 404

    # Lista os detalhes de cada mídia associada ao paciente
    bucket = get_or_create_bucket(bucket_name)
    media_details = []
    for media_key in media_keys:
        blob = bucket.get_blob(media_key)
        if blob:
            media_details.append({
                "Blob ID": blob.id,
                "Filename": blob.name,
                "Size (bytes)": blob.size,
                "URL": blob.public_url,
                "Media Key": media_key  # Adicionando a chave de mídia
            })

    return render_template("mms/list_patient_media.html", media_list=media_details, patient_id=patient_id)




@app.route("/mms/show_media/<media_key>")
def view_media(media_key):
    """Redireciona para a visualização da mídia armazenada no Google Cloud Storage."""
    bucket = get_or_create_bucket(bucket_name)
    blob = bucket.get_blob(media_key)

    if not blob:
        return "Media not found", 404

    # Redireciona para a URL pública do arquivo
    return redirect(blob.public_url)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)