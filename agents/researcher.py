import os
from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient
from core.state import MigrationState

def research_migration(state: MigrationState) -> dict:
    target_dependency = state.get("target_dependency")
    target_version = state.get("target_version")
    
    # Initialize Tavily
    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    tavily_client = TavilyClient(api_key=tavily_api_key)
    
    # Search for migration guide and breaking changes
    query = f"{target_dependency} migration guide to version {target_version} breaking changes"
    search_results = tavily_client.search(query=query, search_depth="advanced")
    context = search_results.get("results", [])
    
    context_str = "\n\n".join([f"Source: {res.get('url')}\nContent: {res.get('content')}" for res in context])
    
    prompt = f"""
    You are an expert AI software engineer. Analyze the following search results about migrating {target_dependency} to version {target_version}.
    Extract a structured list of actionable code modification rules to handle breaking changes.
    Provide the rules as a clear, concise bulleted list.
    
    Search Results Context:
    {context_str}
    """
    
    # Initialize Gemini as primary LLM
    try:
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.8-flash",
            google_api_key=gemini_api_key,
            max_retries=3
        )
        response = llm.invoke(prompt)
    except Exception as e:
        print(f"   ⚠️  Gemini API failed ({e}). Falling back to Groq (openai/gpt-oss-120b)...")
        from langchain_openai import ChatOpenAI
        groq_api_key = os.environ.get("GROQ_API_KEY")
        llm = ChatOpenAI(
            model="openai/gpt-oss-120b",
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_api_key,
            max_retries=3
        )
        response = llm.invoke(prompt)
    
    # Process response into a list of rules
    rules_text = response.content
    if isinstance(rules_text, list):
        parts = []
        for p in rules_text:
            if isinstance(p, dict) and "text" in p:
                parts.append(p["text"])
            elif isinstance(p, str):
                parts.append(p)
            else:
                parts.append(str(p))
        rules_text = "\n".join(parts)
    elif not isinstance(rules_text, str):
        rules_text = str(rules_text)
        
    rules_list = [rule.strip() for rule in rules_text.split('\n') if rule.strip() and (rule.strip().startswith('-') or rule.strip().startswith('*') or rule[0].isdigit())]
    
    # Fallback if no bullet points found
    if not rules_list:
        rules_list = [rules_text]
        
    return {"migration_rules": rules_list}
