document.addEventListener("DOMContentLoaded", function() {
    const textTab = document.getElementById('textTab');
    const markdownTab = document.getElementById('markdownTab');
    const input = document.getElementById('rawText');
    const output = document.getElementById('output');

    function selectTextTab() {
        textTab.classList.add('active');
        markdownTab.classList.remove('active');
	output.classList.remove('display');
        output.classList.add('hide');
        input.classList.remove('hide');
        input.classList.add('display');
    }

    // Convert Markdown table with custom ||a||b||c|| headers to marked format single pipes
    // and using "|-|-|-|" header form terminator row
    // todo: still some confusion with extra newlines that marked seems to ignore
    function convertMarkdownTable(markdownText) {
	// if there is table markdown, change the style to the one marked supports.
	// marked requires a separator row "|--|--|--" after the header
	{
	    const has_table_markdown = /^\s*\|.*\|\s*$/m;
	    if (! has_table_markdown.test(markdownText)) {
		return markdownText;
	    } else {
		markdownText = markdownText.replace(/\|\s*\n\s*\|/g, '|\n|');
	    }
	}
	
	return markdownText
	    .split('\n')
	    .map((line, index, lines) => {
		// look for `||header 1||header 2||` and convert table syntax
		if (line.startsWith('||') && line.endsWith('||')) {
		    // Convert the header row and prepare the separator row
		    const formattedHeaders = line
		          .slice(2, -2)
		          .split('||')
		          .map(header => header.trim())
		          .join(' | ');

		    const separatorRow = '| ' + formattedHeaders.replace(/[^|]+/g, '---') + ' |';
		    return `| ${formattedHeaders} |\n${separatorRow}`;
		} else {
		    // Return non-header rows as is
		    return line;
		}
	    })
	    .join('\n');
    }

    function selectMarkdownTab() {
        markdownTab.classList.add('active');
        textTab.classList.remove('active');

        // todo: dom sanitize
	let it = input.innerText;
	let tv = convertMarkdownTable(it);
        let v = marked.parse(tv);
        output.innerHTML = v;

        output.classList.add('display');
        output.classList.remove('hide');
        input.classList.add('hide');
        input.classList.remove('display');

    }

    if (textTab)  {
        textTab.addEventListener('click', selectTextTab);
    }

    if (markdownTab) {
        markdownTab.addEventListener('click', selectMarkdownTab);
    }

    if (markdownTab) {
	selectMarkdownTab();
    }
});

    
