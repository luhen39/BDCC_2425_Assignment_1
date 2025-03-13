document.getElementById('add-patient-form').addEventListener('submit', function(event) {
    event.preventDefault();
    
    const patientData = {
        SUBJECT_ID: document.getElementById('subject_id').value,
        GENDER: document.getElementById('gender').value,
        DOB: document.getElementById('dob').value,
        DOD: document.getElementById('dod').value || null
    };

    axios.post('/patients', patientData)
        .then(function(response) {
            alert('Patient added successfully!');
        })
        .catch(function(error) {
            console.error('Error adding patient:', error);
        });
});
