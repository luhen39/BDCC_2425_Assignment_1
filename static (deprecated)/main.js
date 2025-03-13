// Função para adicionar ou editar um paciente
document.getElementById('add-patient-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const patientData = {
        SUBJECT_ID: document.getElementById('subject_id').value,
        GENDER: document.getElementById('gender').value,
        DOB: document.getElementById('dob').value,
        DOD: document.getElementById('dod').value || null  // Caso o DOD não seja fornecido
    };

    const submitButton = document.querySelector('button[type="submit"]');
    
    // Se o botão foi alterado para "Edit", o paciente será atualizado
    if (submitButton.textContent === 'Edit Patient') {
        axios.put(`/patients/${patientData.SUBJECT_ID}`, patientData)
            .then(function(response) {
                alert('Patient updated successfully!');
                submitButton.textContent = 'Add Patient';  // Reseta o botão para "Add Patient"
                clearForm();  // Limpa o formulário
                fetchPatients();  // Atualiza a lista de pacientes
            })
            .catch(function(error) {
                console.error('Error updating patient:', error);
            });
    } else {
        // Adiciona novo paciente
        axios.post('/patients', patientData)
            .then(function(response) {
                alert('Patient added successfully!');
                clearForm();  // Limpa o formulário
                fetchPatients();  // Atualiza a lista de pacientes após a criação
            })
            .catch(function(error) {
                console.error('Error adding patient:', error);
            });
    }
});

// Função para buscar a lista de pacientes
function fetchPatients() {
    axios.get('/patients')
        .then(function(response) {
            const patients = response.data;
            const patientList = document.getElementById('patient-list');
            patientList.innerHTML = '';  // Limpa a lista anterior

            patients.forEach(function(patient) {
                const li = document.createElement('li');
                li.textContent = `ID: ${patient.SUBJECT_ID}, Gender: ${patient.GENDER}, DOB: ${patient.DOB}, DOD: ${patient.DOD || 'N/A'}`;
                
                // Adiciona botão de editar
                const editButton = document.createElement('button');
                editButton.textContent = 'Edit';
                editButton.addEventListener('click', function() {
                    editPatient(patient);
                });

                // Adiciona botão de excluir
                const deleteButton = document.createElement('button');
                deleteButton.textContent = 'Delete';
                deleteButton.addEventListener('click', function() {
                    deletePatient(patient.SUBJECT_ID);
                });

                li.appendChild(editButton);
                li.appendChild(deleteButton);
                patientList.appendChild(li);
            });
        })
        .catch(function(error) {
            console.error('Error fetching patients:', error);
        });
}

// Função para deletar um paciente
function deletePatient(subjectId) {
    axios.delete(`/patients/${subjectId}`)
        .then(function(response) {
            alert('Patient deleted successfully!');
            fetchPatients();  // Atualiza a lista de pacientes após a exclusão
        })
        .catch(function(error) {
            console.error('Error deleting patient:', error);
        });
}

// Função para editar um paciente (preenche o formulário com os dados do paciente selecionado)
function editPatient(patient) {
    document.getElementById('subject_id').value = patient.SUBJECT_ID;
    document.getElementById('gender').value = patient.GENDER;
    document.getElementById('dob').value = patient.DOB;
    document.getElementById('dod').value = patient.DOD || '';

    // Muda o botão para "Edit Patient"
    document.querySelector('button[type="submit"]').textContent = 'Edit Patient';
}

// Função para limpar o formulário
function clearForm() {
    document.getElementById('subject_id').value = '';
    document.getElementById('gender').value = '';
    document.getElementById('dob').value = '';
    document.getElementById('dod').value = '';
}

// Função para carregar a lista de pacientes quando a página for carregada
window.onload = function() {
    fetchPatients();
};
