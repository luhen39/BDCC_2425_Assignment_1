document.getElementById('edit-patient-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const subjectId = document.getElementById('subject_id').value;
    const patientData = {
        GENDER: document.getElementById('gender').value,
        DOB: document.getElementById('dob').value,
        DOD: document.getElementById('dod').value || null
    };

    axios.put(`/patients/${subjectId}`, patientData)
        .then(function(response) {
            alert('Patient updated successfully!');
        })
        .catch(function(error) {
            console.error('Error updating patient:', error);
        });
});
