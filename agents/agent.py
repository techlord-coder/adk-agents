import os
from dotenv import load_dotenv

# 1. Look for a file named '.env' in the current folder, parse it,
# and load its keys directly into the system environment memory layer.
load_dotenv()

# 2. Extract the specific secret key string by its unique key label name
api_key = os.getenv("GOOGLE_API_KEY")

from google.adk.agents.llm_agent import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool


def generate_report_pdf(search_results: list, filename:str,reportTitle:str):
    """ Pass a list of strings each item representing a pragraph of the report you generated
    then the name of the pdf file to be generated and the title of the report. The function will generate a pdf report based on the search results.
    Args:
        search_results (list): search_results (list): A STRICT JSON list of strings. 
            DO NOT merge paragraphs into one string. 
            Each element in this list must be a single, distinct paragraph.
            Example: ["Paragraph one text.", "Paragraph two text.", "Paragraph three text."]
        filename (str): The name of the pdf file to be generated. Should be unique for each pdf report generated based on the report title.
        reportTitle (str): The title of the report
    """
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT

    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(f"{filename}",pagesize=letter, rightMargin=72,leftMargin=72,topMargin=72,bottomMargin=18)
    head_style=ParagraphStyle('Heading', parent=styles['Heading1'], fontSize=18, leading=22, alignment=TA_CENTER)
    body_style=ParagraphStyle('Body', parent=styles['Normal'], fontSize=12, leading=14)
    story = []
    heading = Paragraph(reportTitle, head_style)
    story.append(heading)
    story.append(Spacer(1, 12))
    for result in search_results:
        body = Paragraph(result, body_style)
        story.append(body)
        story.append(Spacer(1, 12))
    doc.build(story)
#The 3 research sub-agents

treatment_specialist = Agent(
    model='gemini-2.5-pro',
    name='treatment_specialist',
    description="Researches highly trending spa procedures and biological benefits.",
    instruction="""You are a wellness researcher. Identify 5 popular, viral spa treatments 
    (e.g., HydraFacials, hot stone massage). Write an in-depth analysis of each treatment, including the biological benefits they provide, the physiological mechanisms behind those benefits, and any scientific studies that support their effectiveness. Include information on how these treatments impact stress levels, skin health, and overall well-being. Pass your findings to the root agent for further analysis.
    Use the google_search tool to gather information about the treatments, their benefits, and any relevant scientific studies. Ensure that your findings are well-researched, accurate, and provide a comprehensive understanding of each treatment's impact on health and wellness.
    """ ,
    tools=[google_search]
)
feedback_analyst = Agent(
    model='gemini-2.5-pro',
    name='feedback_analyst',
    description="Audits customer complaints to find common spa complaints.",
    instruction="""You are a consumer advocate. Research online spa reviews and identify 5 common frustrations or pitfalls customers complain about. 
    Write an in-depth analysis of each complaint, including the underlying reasons for the dissatisfaction. Pass your findings to the root agent for further analysis.
    Use the google_search tool to gather information about common spa complaints, customer reviews, and any relevant articles or studies that discuss these issues. Ensure that your findings are well-researched, accurate, and provide a comprehensive understanding of the common frustrations customers experience in spa settings.
    """,
    tools=[google_search]
)

motivation_analyst = Agent(
    model='gemini-2.5-pro',
    name='motivation_analyst',
    description="Analyzes consumer psychological and stress triggers.",
    instruction="""You are a wellness psychologist. Research the psychological and stress-related triggers that drive consumers to seek spa treatments. Identify 5 key motivations, such as stress relief, self-care, or social influence. Write an in-depth analysis of each motivation, including the psychological mechanisms behind them and how they influence consumer behavior. Pass your findings to the root agent for further analysis.
    Use the google_search tool to gather information about consumer psychology, stress triggers, and any relevant studies or articles that discuss these motivations. Ensure that your findings are well-researched, accurate, and provide a comprehensive understanding of the psychological factors that drive consumers to seek spa treatments.
    """,
    tools=[google_search]
)

treatment_specialist_tool=AgentTool(agent=treatment_specialist)
feedback_analyst_tool=AgentTool(agent=feedback_analyst)
motivation_analyst_tool=AgentTool(agent=motivation_analyst)

root_agent = Agent(
    model='gemini-2.5-pro',
    name="research_orchestrator",
    description="You are a research lead. Your task is to orchestrate the research process by coordinating the efforts of the three sub-agents: treatment_specialist, feedback_analyst, and motivation_analyst. You will receive their findings and synthesize them into  comprehensive reports that provides actionable insights for spa businesses.",
    instruction="""You are a research lead.
                1.First invoke all three research tools: treatment_specialist_tool, feedback_analyst_tool, and motivation_analyst_tool to gather their findings.
                2.Wait for all the results from the tools . This is crucial to ensure you have a complete picture of the research landscape.
                3.Once you have received all the findings, synthesize the information into several comprehensive reports. Each report should provide actionable insights for spa businesses, focusing on the most effective treatments, common customer complaints, and key psychological motivations driving consumer behavior.Minimum of 30 in-depth reports should be generated.
                4. For each report, generate a PDF file using the generate_report_pdf function. The filename should be unique for each report and should reflect the content of the report. The title of each report should be clear and descriptive, indicating the focus of the insights provided.
                """,
    tools=[treatment_specialist_tool, feedback_analyst_tool, motivation_analyst_tool,generate_report_pdf]
)