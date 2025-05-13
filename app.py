import streamlit as st
import pandas as pd
import os
import io
import re
import PyPDF2
import docx2txt
import json
import time
import requests
from io import StringIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Configuration for the OpenAI API
OPENAI_API_TYPE = "azure"
OPENAI_API_BASE = "https://bfslabopenai.openai.azure.com/"
OPENAI_API_VERSION = "2023-05-15"
OPENAI_MODEL_NAME_GPT4 = "gpt-4"
OPENAI_DEPLOYMENT_NAME_GPT4 = "BFSLABAUSGPT4"
OPENAI_API_KEY_GPT4 = "68a4beec201548f889287641f6ba9401"
OPENAI_DEPLOYMENT_ENDPOINT_GPT4 = "https://bsflabaus.openai.azure.com/"

# Set page configuration
st.set_page_config(
    page_title="ATS Resume Analyzer", 
    page_icon="📄", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #333;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .score-high {
        color: #4CAF50;
        font-weight: bold;
    }
    .score-medium {
        color: #FF9800;
        font-weight: bold;
    }
    .score-low {
        color: #F44336;
        font-weight: bold;
    }
    .scrollable-text {
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid #e6e6e6;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 20px;
    }
    .suggestion-btn {
        background-color: #4CAF50;
        color: white;
        padding: 10px 15px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;
        margin: 10px 0;
    }
    .suggestion-btn:hover {
        background-color: #45a049;
    }
    .feature-checkbox {
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session states
if 'analyzed_results' not in st.session_state:
    st.session_state.analyzed_results = {}
if 'jd_text' not in st.session_state:
    st.session_state.jd_text = ""
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'resume_texts' not in st.session_state:
    st.session_state.resume_texts = {}
if 'resume_descriptions' not in st.session_state:
    st.session_state.resume_descriptions = {}
if 'improvement_suggestions' not in st.session_state:
    st.session_state.improvement_suggestions = {}
if 'analysis_features' not in st.session_state:
    st.session_state.analysis_features = {
        'technical_skills': False,
        'experience_depth': False,
        'education_quality': False,
        'certifications': False,
        'soft_skills': False,
        'project_complexity': False,
        'industry_alignment': False,
        'leadership_potential': False
    }

# OpenAI API integration
def generate_gpt_response(prompt, system_prompt=None, temperature=0.7, max_retries=3):
    """Generate response"""
    url = f"{OPENAI_DEPLOYMENT_ENDPOINT_GPT4}/openai/deployments/{OPENAI_DEPLOYMENT_NAME_GPT4}/chat/completions?api-version={OPENAI_API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "api-key": OPENAI_API_KEY_GPT4
    }
    
    # Prepare messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "messages": messages,
        "max_tokens": 1500,
        "temperature": temperature
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retrying
                continue
            else:
                st.error(f"Failed to communicate  after {max_retries} attempts: {str(e)}")
                return "Error: Could not get a response from the AI."

# Define the system prompts
RESUME_SCORING_SYSTEM_PROMPT = """
You are an expert ATS (Applicant Tracking System) scoring engine. 
Your task is to score a resume against a job description on a scale of 0-100.
Provide the overall score and sub-scores for key categories in JSON format only.
"""

RESUME_ANALYSIS_SYSTEM_PROMPT = """
You are an expert ATS (Applicant Tracking System) analyst and professional resume consultant.
Your task is to analyze a resume against a job description and provide detailed feedback.
Be thorough, honest, and constructive in your analysis.
"""

RESUME_IMPROVEMENT_SYSTEM_PROMPT = """
You are an expert resume consultant. 
Your task is to provide specific, actionable suggestions to improve a resume for a particular job.
Focus on the most important gaps and opportunities for improvement.
"""

# Text extraction functions
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

def extract_text_from_docx(file):
    text = docx2txt.process(file)
    return text

def extract_text_from_txt(file):
    return file.getvalue().decode("utf-8")

def extract_text(file):
    file_ext = os.path.splitext(file.name)[1].lower()
    if file_ext == '.pdf':
        return extract_text_from_pdf(file)
    elif file_ext == '.docx':
        return extract_text_from_docx(file)
    elif file_ext == '.txt':
        return extract_text_from_txt(file)
    else:
        st.error(f"Unsupported file format: {file_ext}")
        return None

def analyze_resume(resume_text, jd_text, resume_name):
    # Construct the prompt based on selected features
    features_list = [
        feature.replace('_', ' ').title() 
        for feature, is_selected in st.session_state.analysis_features.items() 
        if is_selected
    ]
    
    # If no features are selected, use default
    if not features_list:
        features_list = ["Overall Match"]
    
    features_str = ", ".join(features_list)
    
    # Create scoring prompt
    scoring_prompt = f"""
    # Job Description:
    {jd_text}
    
    # Resume:
    {resume_text}
    
    Score this resume's match across these features: {features_str}
    Provide a comprehensive score on a scale of 0-100.
    Return ONLY an integer score and no other text.
    """
    
    # Get score from GPT-4
    score_result = generate_gpt_response(scoring_prompt, RESUME_SCORING_SYSTEM_PROMPT, 0.2)
    
    # Try to parse the score
    try:
        score = int(score_result.strip())
        # Ensure score is between 0 and 100
        score = max(0, min(score, 100))
    except (ValueError, TypeError):
        # Fallback to a default score if parsing fails
        score = 65
    
    return {
        "name": resume_name,
        "score": score
    }

def generate_resume_description(resume_text, jd_text):
    # Construct the prompt based on selected features
    features_list = [
        feature.replace('_', ' ').title() 
        for feature, is_selected in st.session_state.analysis_features.items() 
        if is_selected
    ]
    
    # If no features are selected, use default
    if not features_list:
        features_list = ["Overall Match"]
    
    features_str = ", ".join(features_list)
    
    # Create analysis prompt
    analysis_prompt = f"""
    # Job Description:
    {jd_text}
    
    # Resume:
    {resume_text}
    
    Please analyze this resume focusing on these key features: {features_str}.
    Provide a detailed yet concise description of how well the resume matches the job description.
    Highlight strengths and potential areas for improvement.
    Keep your response to 4-6 sentences.
    """
    
    # Get analysis from GPT-4
    return generate_gpt_response(analysis_prompt, RESUME_ANALYSIS_SYSTEM_PROMPT, 0.7)

def generate_improvement_suggestions(resume_text, jd_text):
    # Construct the prompt based on selected features
    features_list = [
        feature.replace('_', ' ').title() 
        for feature, is_selected in st.session_state.analysis_features.items() 
        if is_selected
    ]
    
    # If no features are selected, use default
    if not features_list:
        features_list = ["Overall Match"]
    
    features_str = ", ".join(features_list)
    
    improvement_prompt = f"""
    # Job Description:
    {jd_text}
    
    # Resume:
    {resume_text}
    
    Based on the job description and focusing on these features: {features_str}, 
    provide 5 specific, actionable suggestions to improve this resume.
    Focus on the most impactful changes that would increase the candidate's 
    chances of getting past the ATS and impressing the hiring manager.
    For each suggestion, provide a concrete example of how to implement it.
    """
    
    # Get improvement suggestions from GPT-4
    return generate_gpt_response(improvement_prompt, RESUME_IMPROVEMENT_SYSTEM_PROMPT, 0.7)

# Sidebar
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>⚙️ Analysis Settings</h1>", unsafe_allow_html=True)
    
    st.markdown("### Select Analysis Features")
    
    # Create checkboxes for analysis features
    feature_config = [
        ('technical_skills', 'Technical Skills'),
        ('experience_depth', 'Work Experience Depth'),
        ('education_quality', 'Education Quality'),
        ('certifications', 'Certifications'),
        ('soft_skills', 'Soft Skills'),
        ('project_complexity', 'Project Complexity'),
        ('industry_alignment', 'Industry Alignment'),
        ('leadership_potential', 'Leadership Potential')
    ]
    
    # Display checkboxes and update session state
    for key, label in feature_config:
        st.session_state.analysis_features[key] = st.checkbox(
            label, 
            value=st.session_state.analysis_features.get(key, False),
            key=f"feature_{key}",
            help=f"Include {label.lower()} in resume analysis"
        )
    
    st.markdown("---")
    st.markdown("<h3>Instructions</h3>", unsafe_allow_html=True)
    st.markdown("""
    1. Select desired analysis features
    2. Upload a job description
    3. Upload one or more resumes
    4. Click "Analyze Resumes"
    """)
    
    # Add API status indicator
    st.markdown("---")
    st.markdown("### API Status")
    st.info("Using LLama3")

# Main content
st.markdown("<h1 class='main-header'>📄 ATS Resume Analyzer</h1>", unsafe_allow_html=True)

# Create two tabs
tab1, tab2 = st.tabs(["Upload Files", "Analysis Results"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h2 class='sub-header'>Job Description</h2>", unsafe_allow_html=True)
        jd_file = st.file_uploader("Upload Job Description", type=["pdf", "docx", "txt"], key="jd_uploader")
        
        if jd_file:
            jd_text = extract_text(jd_file)
            if jd_text:
                st.session_state.jd_text = jd_text
                st.success(f"Job description uploaded: {jd_file.name}")
                with st.expander("View Job Description"):
                    st.markdown("<div class='scrollable-text'>", unsafe_allow_html=True)
                    st.text_area("", jd_text, height=300, disabled=True)
                    st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h2 class='sub-header'>Resumes</h2>", unsafe_allow_html=True)
        resume_files = st.file_uploader("Upload Resumes", type=["pdf", "docx", "txt"], accept_multiple_files=True, key="resume_uploader")
        
        if resume_files:
            st.success(f"{len(resume_files)} resume(s) uploaded")
            with st.expander("View Uploaded Resumes"):
                for file in resume_files:
                    st.write(f"• {file.name}")
    
    if st.session_state.jd_text and resume_files:
        if st.button("Analyze Resumes", key="analyze_button", type="primary", use_container_width=True):
            with st.spinner("Analyzing resumes ... This may take a few minutes."):
                # Analyze each resume
                st.session_state.analyzed_results = {}
                st.session_state.resume_texts = {}
                st.session_state.resume_descriptions = {}
                for file in resume_files:
                    resume_text = extract_text(file)
                    if resume_text:
                        # Store the resume text for later use with suggestions
                        st.session_state.resume_texts[file.name] = resume_text
                        # Analyze the resume
                        result = analyze_resume(resume_text, st.session_state.jd_text, file.name)
                        st.session_state.analyzed_results[file.name] = result
                        
                        # Generate description for the resume
                        description = generate_resume_description(resume_text, st.session_state.jd_text)
                        st.session_state.resume_descriptions[file.name] = description
                
                st.session_state.analysis_complete = True

with tab2:
    if not st.session_state.analysis_complete:
        st.info("Please upload job description and resumes, then run analysis to see results.")
    else:
        # Selected analysis features display
        selected_features = [
            feature.replace('_', ' ').title() 
            for feature, is_selected in st.session_state.analysis_features.items() 
            if is_selected
        ]
        
        # Ranking View
        st.markdown(f"<h2 class='sub-header'>Resume Ranking - {', '.join(selected_features or ['Overall Match'])}</h2>", unsafe_allow_html=True)
        
        # Convert results to a DataFrame for easy sorting
        results_data = list(st.session_state.analyzed_results.values())
        df = pd.DataFrame(results_data)
        df = df.sort_values('score', ascending=False)
        
        # Style the DataFrame
        def color_score(score):
            if score >= 80:
                return 'background-color: #c6efce; color: #006100'
            elif score >= 60:
                return 'background-color: #ffeb9c; color: #9c5700'
            else:
                return 'background-color: #ffc7ce; color: #9c0006'
        
        # Create styled dataframe
        styled_df = df.style.applymap(color_score, subset=['score'])
        
        # Display the table
        st.dataframe(
            styled_df, 
            column_config={
                "name": "Resume Name",
                "score": st.column_config.NumberColumn(
                    "Match Score",
                    help="Scoring based on selected analysis features",
                    format="%d %%"
                )
            },
            hide_index=True,
            use_container_width=True
        )

        # Selected features display
        if selected_features:
            st.markdown("### Selected Analysis Features")
            feature_chips = " ".join([f"<span style='background-color:#e6f2ff; padding:5px; margin:2px; border-radius:5px; display:inline-block;'>{feature}</span>" for feature in selected_features])
            st.markdown(feature_chips, unsafe_allow_html=True)

        # Select a resume for detailed view
        selected_resume = st.selectbox(
            "Select a resume to view details:", 
            options=df['name'].tolist()
        )
        
        if selected_resume:
            # Find the selected resume's details
            resume_details = st.session_state.analyzed_results[selected_resume]
            
            # Display resume details
            st.markdown(f"### Details for {selected_resume}")
            st.markdown(f"""
            **Match Score**: 
            <span class='{"score-high" if resume_details["score"] >= 80 else "score-medium" if resume_details["score"] >= 60 else "score-low"}'>
            {resume_details["score"]}%
            </span>
            """, unsafe_allow_html=True)
            
            # Display resume description
            if selected_resume in st.session_state.resume_descriptions:
                st.markdown("### Resume Analysis")
                st.markdown(f"<div class='scrollable-text'>{st.session_state.resume_descriptions[selected_resume]}</div>", unsafe_allow_html=True)
            
            # Add button to generate improvement suggestions
            if st.button("Generate Improvement Suggestions", key=f"improve_{selected_resume}"):
                with st.spinner("Generating suggestions..."):
                    if selected_resume in st.session_state.resume_texts:
                        resume_text = st.session_state.resume_texts[selected_resume]
                        # Generate suggestions
                        suggestions = generate_improvement_suggestions(resume_text, st.session_state.jd_text)
                        # Store suggestions
                        st.session_state.improvement_suggestions[selected_resume] = suggestions
            
            # Display improvement suggestions if they exist
            if selected_resume in st.session_state.improvement_suggestions:
                st.markdown("### Improvement Suggestions")
                st.markdown(f"<div class='scrollable-text'>{st.session_state.improvement_suggestions[selected_resume]}</div>", unsafe_allow_html=True)

# Hide Streamlit default elements
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
