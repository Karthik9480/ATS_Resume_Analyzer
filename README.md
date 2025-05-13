# ATS Resume Analyzer

A Streamlit application that uses AI (Ollama) to analyze resumes against job descriptions, providing scores, detailed analysis, and improvement suggestions.

## Features

- **Job Description Upload**: Upload job descriptions in PDF, DOCX, or TXT formats
- **Multiple Resume Upload**: Analyze multiple resumes at once
- **Customizable Analysis**: Select specific analysis features to focus on
- **Resume Ranking**: Sort resumes by match score
- **Detailed Insights**: Get comprehensive analysis for each resume
- **Improvement Suggestions**: Receive actionable suggestions to improve each resume
- **Interactive UI**: User-friendly interface with expandable sections and score highlighting

## Analysis Features

- Technical Skills Assessment
- Work Experience Depth
- Education Quality
- Certifications Analysis
- Soft Skills Evaluation
- Project Complexity Analysis
- Industry Alignment
- Leadership Potential Assessment

## Requirements

- Python 3.8+
- Ollama running locally (for LLM integration)
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/Karthik9480/ATS_Resume_Analyzer.git
   cd ats-resume-analyzer
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Setup Ollama:
   - Install [Ollama](https://ollama.ai/download)
   - Ensure the llama3 model is available:
     ```
     ollama pull llama3
     ```
   - Make sure Ollama is running on localhost:11434

## Usage

1. Run the Streamlit app:
   ```
   streamlit run app.py
   ```

2. Open your web browser and navigate to the local URL shown in the terminal (typically http://localhost:8501)

3. In the app:
   - Select desired analysis features from the sidebar
   - Upload a job description file
   - Upload one or more resume files
   - Click "Analyze Resumes"
   - View ranking and detailed analysis in the "Analysis Results" tab
   - Generate improvement suggestions for any resume

## File Format Support

- PDF (.pdf)
- Microsoft Word (.docx)
- Plain Text (.txt)

## Technical Implementation

- **Streamlit**: For the web interface
- **LLM Integration**: Using Ollama with llama3 model for AI analysis
- **Concurrent Processing**: ThreadPoolExecutor for handling multiple resumes
- **Text Extraction**: Supports multiple document formats

## Future Enhancements

- Export results as PDF or CSV
- Save analysis history
- Support for more file formats
- Integration with more LLM options
- Enhanced visualization of resume scores
- Comparative analysis between resumes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
