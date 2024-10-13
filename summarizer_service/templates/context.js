document.addEventListener("DOMContentLoaded", function() {
    var contextTextarea = document.querySelector('textarea[name="context"]');

    // Use event delegation to listen for clicks on the clear button (the [X] text)
    contextTextarea.addEventListener("click", function(e) {
	// Check if the clicked target is the [X]
	if (e.target.textContent === "[X]") {
	    contextTextarea.value = ""; // Clear the textarea
	}
    });
});

    
