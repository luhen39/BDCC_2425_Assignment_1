document.getElementById('delete-patient-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const subjectId = document.getElementById('subject_id').value;

    axios.delete(`/patients/${subjectId}`)
        .then(function(response) {
            alert('Patient deleted successfully!');
        })
        .catch(function(error) {
            console.error('Error deleting patient:', error);
        });
});
