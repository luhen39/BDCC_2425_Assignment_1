function fetchPatients() {
    axios.get('/patients')
        .then(function(response) {
            const patients = response.data;
            const patientList = document.getElementById('patient-list');
            patientList.innerHTML = '';

            patients.forEach(function(patient) {
                const li = document.createElement('li');
                li.textContent = `ID: ${patient.SUBJECT_ID}, Gender: ${patient.GENDER}, DOB: ${patient.DOB}, DOD: ${patient.DOD || 'N/A'}`;
                patientList.appendChild(li);
            });
        })
        .catch(function(error) {
            console.error('Error fetching patients:', error);
        });
}
