document.addEventListener("DOMContentLoaded", function() {
    const textTab = document.getElementById('textTab');
    const markdownTab = document.getElementById('markdownTab');
    const input = document.getElementById('rawText');
    const output = document.getElementById('output');

    function selectTextTab() {
        console.log("textTab click", textTab);
        textTab.classList.add('active');
        markdownTab.classList.remove('active');
	output.classList.remove('display');
        output.classList.add('hide');
        input.classList.remove('hide');
        input.classList.add('display');
    }

    function selectMarkdownTab() {
	console.log("markdownTab click", markdownTab);
	console.log("markdownTab innerText", input.innerText);
        markdownTab.classList.add('active');
        textTab.classList.remove('active');

        // todo: dom sanitize
        let v = marked.parse(input.innerText);
	console.log("markdownTab: setting output.innerHTML to  v", v);
        output.innerHTML = v;

        output.classList.add('display');
        output.classList.remove('hide');
        input.classList.add('hide');
        input.classList.remove('display');

    }

    if (textTab)  {
        console.log("adding event listener to textTab", textTab);
        textTab.addEventListener('click', selectTextTab);
    }

    if (markdownTab) {
        console.log("adding event listener to markdownTab", markdownTab);
        markdownTab.addEventListener('click', selectMarkdownTab);
    }

    if (markdownTab) {
	console.log("calling setupMarkdownDisplay");
	selectMarkdownTab();
    }
});

    
