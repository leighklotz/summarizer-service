document.addEventListener("DOMContentLoaded", function() {
    var form = document.querySelector("form");
    var submitButton = document.getElementById("submit-button");
    var loadingAnimation = document.getElementById("loading");

    form.addEventListener("submit", function() {
        submitButton.disabled = true;
        loadingAnimation.style.display = "block";
    });
});

