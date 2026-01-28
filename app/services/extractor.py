import json
import re
from app.services.ollama_service import ask_llm

def extract_insights_and_tasks(mail_body, available_tags=None):
    """
    Analyzes email content using Mistral (English Prompt).
    outputs JSON with:
    1. 'task': null or {title, date}
    2. 'insight': string
    3. 'category': "Proposal", "Complaint", "Payment", "Question", "Meeting", "Other"
    4. 'urgency_score': 0-100
    5. 'tags': List of slugs matched from available_tags
    """

    # Prepare tag list for the prompt
    tag_list_str = "[]"
    valid_slugs = set()
    
    if available_tags:
        # [{slug: 'fatura', description: '...'}, ...]
        tag_lines = []
        for t in available_tags:
            slug = t.get('slug')
            desc = t.get('description', '')
            if slug:
                tag_lines.append(f"- {slug}: {desc}")
                valid_slugs.add(slug)
        tag_list_str = "\n    " + "\n    ".join(tag_lines)

    prompt = f"""
    You are a professional executive assistant. 
    Analyze the following email content and return only the result in JSON format.
    The email can be in Turkish or English.

    AVAILABLE TAG LIST (Use only these slugs):
    {tag_list_str}

    ANALYSIS CRITERIA:
    1. 'task': Is there a meeting, deadline, or actionable task? 
       If yes, provide a short title and date (YYYY-MM-DD). If no clear date, use null.
    2. 'insight': Any permanent information about the sender/company? (e.g. "Leaves early on Fridays").
    3. 'category': Classify into one of: "Proposal", "Complaint", "Payment", "Question", "Meeting", "Other".
    4. 'urgency_score': How urgent is this? (0-100).
       - CRITICAL (80-100): System crash, payment failure, security breach, deadline today.
       - TIME-SENSITIVE (60-79): Meeting invite, task for today/tomorrow, approval needed.
       - NORMAL (30-59): Info request, process update, internal comms.
       - PASSIVE (0-29): Newsletter, announcement, "FYI", casual chat.
    5. 'is_proposal': Is this a proposal or a question requiring approval? (True/False).
    6. 'tags': Review the "AVAILABLE TAG LIST" above. 
       - Select strictly from the provided 'slugs'.
       - **LANGUAGE SUPPORT:** The available tags are now in English. 
       - If the content matches the tag description, add the tag.
       - e.g. "Invoice" -> "finance", "Meeting" -> "meeting".
       - Select strictly from the provided 'slugs'.
       - Do not make up tags. If none match, return empty list.

    EMAIL CONTENT:
    {mail_body}

    RESPONSE FORMAT (JSON Example - DO NOT COPY VALUES):
    {{
        "task": null, 
        "insight": "Sender is usually busy on Mondays...",
        "category": "Other",
        "urgency_score": 50,
        "is_proposal": false,
        "tags": [] 
    }}
    """

    try:
        # Mistral with JSON mode
        raw_response = ask_llm(prompt, json_mode=True)
        
        # Extract JSON
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            
            # Defaults and Safety
            if "task" not in data: data["task"] = None
            if "insight" not in data: data["insight"] = None
            if "category" not in data: data["category"] = "Other"
            if "urgency_score" not in data: data["urgency_score"] = 0
            if "is_proposal" not in data: data["is_proposal"] = False
            if "tags" not in data: data["tags"] = []
            
            # Tag Validation
            if valid_slugs and isinstance(data["tags"], list):
                 original_tags = data["tags"]
                 data["tags"] = [t for t in original_tags if t in valid_slugs]
                 if len(original_tags) != len(data["tags"]):
                     print(f"⚠️ Invalid tags removed: {set(original_tags) - set(data['tags'])}")
            
            return data
        
        return {"task": None, "insight": None, "category": "Other", "urgency_score": 0, "is_proposal": False, "tags": []}

    except Exception as e:
        print(f"❌ Smart Extraction Error: {e}")
        return {"task": None, "insight": None, "category": "Other", "urgency_score": 0, "is_proposal": False, "tags": []}