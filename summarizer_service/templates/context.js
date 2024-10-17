// Object to store the content of the textarea before it is cleared
const textareaUndo = {};

// Function to toggleTextareaContent or restore the content of the textarea based on the button state
function toggleTextareaContent(button) {
    // Find the parent container and the textarea inside it
    const container = button.parentElement;
    const textarea = container.querySelector('textarea');

    // If the button text content is [X], clear the textarea and store its value
    if (button.textContent === "[X]") {
        textareaUndo[textarea.id] = textarea.value;
        button.textContent = "<!>";
        textarea.value = ' ';	// hack to make sure it gets sent in the POST and is not empty
    }
    else if (button.textContent === "<!>") {
        // If the button text content is <!>, restore the textarea content
        const current_value = textarea.value;
        const undo_value = textareaUndo[textarea.id];
        if (undo_value) {
            if (current_value !== '') {
                textareaUndo[textarea.id] = current_value;
            } else {
                delete textareaUndo[textarea.id];
            }
            // Restore the saved content, if it exists
            textarea.value = undo_value;
        } else {
            // Clear the textarea if there is no saved content
            textarea.value = ' '; // repeat workaround to override server-side session vars
        }
        button.textContent = "[X]";
    }
    else {
        // Handle unexpected button states
        console.log("unknown click on button.textContent", button.textContent);
    }
}
