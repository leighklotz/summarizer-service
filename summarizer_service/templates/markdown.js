function activateTab(a_tab, a_display) {
    const tabs = [rawTextTab, markdownTab, plainTextTab];
    const displays = [rawText, markdownText, plainText];

    for (let tab of tabs) {
	if (tab === a_tab) {
	    tab.classList.add('active');
	} else {
	    tab.classList.remove('active');
	}
    }

    for (let display of displays) {
	if (display === a_display) {
	    display.classList.remove('hide');
	    display.classList.add('display');
	} else {
	    display.classList.remove('display');
	    display.classList.add('hide');
	}
    }
}


function activateTab(a_tab, a_display) {
    const tabs = [rawTextTab, markdownTab, plainTextTab];
    const displays = [rawText, markdownText, plainText];

    for (let tab of tabs) {
        if (tab === a_tab) {
	    tab.classList.add('active');
        } else {
	    tab.classList.remove('active');
        }
    }

    for (let display of displays) {
        if (display === a_display) {
	    display.classList.remove('hide');
	    display.classList.add('display');
        } else {
	    display.classList.remove('display');
	    display.classList.add('hide');
        }
    }
}

document.addEventListener("DOMContentLoaded", function() {
    const rawTextTab = document.getElementById('rawTextTab');
    const plainTextTab = document.getElementById('plainTextTab');
    const markdownTab = document.getElementById('markdownTab');
    const rawText = document.getElementById('rawText');
    const plainText = document.getElementById('plainText');
    const markdownText = document.getElementById('markdownText');

    function selectRawTextTab() {
	activateTab(rawTextTab, rawText);
    }

    function selectPlainTextTab() {
        activateTab(plainTextTab, plainText);
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

    function sanitize_dom(v) {
	// todo: dom sanitize
	return v;
    }

    function selectMarkdownTab() {
	activateTab(markdownTab, markdownText);

	MathJax.typesetPromise([rawText]).then(() => {
	    console.log("MathJax rendering complete.");
	    let it = rawText.innerText;
	    let tv = convertMarkdownTable(it);
            let v = marked.parse(tv);
 	    let vs = sanitize_dom(v);
            markdownText.innerHTML = v;
	}).catch((err) => {
	    console.error("MathJax rendering error:", err.message);
	});

    }

    const tabEvents = {
	rawTextTab: selectRawTextTab,
	plainTextTab: selectPlainTextTab,
	markdownTab: selectMarkdownTab
    };

    for (const [tabName, eventHandler] of Object.entries(tabEvents)) {
	const tabElement = window[tabName];
	if (tabElement) {
            tabElement.addEventListener('click', eventHandler);
	}
    }
    if (markdownTab) {
	selectMarkdownTab();
    }
});
