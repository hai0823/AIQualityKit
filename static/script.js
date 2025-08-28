document.getElementById('analyze-btn').addEventListener('click', async () => {
    const textInput = document.getElementById('text-input').value;
    const resultsOutput = document.getElementById('results-output');
    
    if (!textInput.trim()) {
        resultsOutput.textContent = 'Please enter some text to analyze.';
        return;
    }

    resultsOutput.textContent = 'Analyzing...';

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: textInput }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const results = await response.json();
        resultsOutput.textContent = JSON.stringify(results, null, 2);

    } catch (error) {
        console.error('Error during analysis:', error);
        resultsOutput.textContent = `An error occurred: ${error.message}`;
    }
});
