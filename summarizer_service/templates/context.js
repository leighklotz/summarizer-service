document.addEventListener("DOMContentLoaded", function() {
    var clearButton = document.getElementById("clear-context");
    var contextTextarea = document.querySelector('textarea[name="context"]');

    clearButton.addEventListener("click", function() {
	contextTextarea.value = "";
    });
});

    
