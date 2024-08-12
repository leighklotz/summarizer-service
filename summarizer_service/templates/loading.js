document.addEventListener("DOMContentLoaded", function() {
    var f = document.getElementById("mainform");
    console.log("form", f);
    if (f) {
	var submitButton = document.getElementById("submit-button");
	var loadingAnimation = document.getElementById("loading");

	f.addEventListener("submit", function() {
            submitButton.disabled = true;
            loadingAnimation.style.display = "block";
	});
    }
});

