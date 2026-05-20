"""
Pluggable Intelligence Providers for OBI 2.0.
Supports Regex (Fast/Free), Ollama (Local LLM), and potentially Cloud APIs.
"""
import json
import os
import re
import requests

# KrutiDev 010 to Unicode mapping (Core markers)
# This allows the machine and LLMs to read legacy-encoded UP budgets.
KRUTIDEV_MAP = {
    "foRr": "वित्त",
    "ea=h": "मंत्री",
    "ctV": "बजट",
    "vuqekuksa": "अनुमानों",
    "Hkk\"k.k": "भाषण",
    "th0,l0Mh0ih0": "जीएसडीपी",
    "yk[k": "लाख",
    "djksM": "करोड़",
    "izfr'kr": "प्रतिशत",
}

def krutidev_to_unicode(text):
    """Simple mapping for core fiscal terms in legacy fonts."""
    for k, v in KRUTIDEV_MAP.items():
        text = text.replace(k, v)
    return text

class BaseProvider:
    def analyze_signals(self, text):
        raise NotImplementedError

class RegexProvider(BaseProvider):
    """
    Primary Deterministic Provider. 
    Budget docs are structured legal instruments; regex should be the main play.
    """
    def __init__(self):
        # Austerity signals: Spending cuts, service freezes, and labor precarity
        self.austerity_markers = [
            r"rationalization", r"freeze", r"expenditure control", r"merger of schemes",
            r"austerity", r"cut", r"reduction", r"efficiency", r"disinvestment",
            r"contractual cadre", r"honorarium", r"fixed term", r"outsource"
        ]
        # Extravagance signals: Capital subsidies and asset-inflation incentives
        self.extravagance_markers = [
            r"concession", r"incentive", r"investor", r"viability gap", r"ppp",
            r"exemption", r"tax holiday", r"subsidy to capital", r"asset inflation",
            r"mega project", r"mou signed", r"global summit"
        ]
        # Unit Discipline signals: To ensure deterministic accounting
        self.unit_markers = [
            r"lakh crore", r"rs\. in cr", r"₹ in cr", r"in thousand"
        ]

    def _count(self, text, markers):
        count = 0
        # Transliterate legacy font (KrutiDev) to Unicode for analysis
        clean_text = krutidev_to_unicode(text.lower())
        for marker in markers:
            count += len(re.findall(marker, clean_text))
        return count

    def analyze_signals(self, text):
        return {
            "austerity_score": self._count(text, self.austerity_markers),
            "extravagance_score": self._count(text, self.extravagance_markers),
            "provider": "regex"
        }

class OllamaProvider(BaseProvider):
    """Local LLM provider using Ollama (e.g. Llama3, Mistral)."""
    def __init__(self, model="llama3", url="http://localhost:11434/api/generate"):
        self.model = model
        self.url = url

    def generate(self, prompt, format=None):
        """General purpose generation."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            if format:
                payload["format"] = format
                
            response = requests.post(self.url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get('response', '')
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}")

    def analyze_signals(self, text):
        # Transliterate legacy font (KrutiDev) to Unicode for analysis
        readable_text = krutidev_to_unicode(text)
        sample = readable_text[:2000]
        prompt = f"""
        Analyze the following budget text using the Melinda Cooper framework.
        Identify signals of:
        1. 'Austerity' (spending cuts, service freezes, rationalization).
        2. 'Extravagance' (capital subsidies, investor incentives, concessions).
        
        Return ONLY a JSON object with two integer scores (0-10) for each category.
        Format: {{"austerity_score": int, "extravagance_score": int}}
        
        TEXT:
        {sample}
        """
        try:
            response = requests.post(self.url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }, timeout=30)
            result = response.json()
            data = json.loads(result['response'])
            data["provider"] = f"ollama:{self.model}"
            return data
        except Exception as e:
            return {"error": str(e), "austerity_score": 0, "extravagance_score": 0, "provider": "ollama:error"}

class OpenRouterProvider(BaseProvider):
    """Cloud provider using OpenRouter to access open-weights models."""
    def __init__(self, model="meta-llama/llama-3-8b-instruct"):
        self.model = model
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        if not self.api_key:
            print("WARNING: OPENROUTER_API_KEY not found in environment.")

    def analyze_signals(self, text):
        if not self.api_key:
            return {"error": "Missing API Key", "austerity_score": 0, "extravagance_score": 0, "provider": "openrouter:error"}
            
        # Transliterate legacy font (KrutiDev) to Unicode for analysis
        readable_text = krutidev_to_unicode(text)
        sample = readable_text[:3000] # Give it enough context for Devanagari
        prompt = f"""
        Analyze the following budget text.
        Identify signals of:
        1. 'Austerity' (spending cuts, service freezes).
        2. 'Extravagance' (capital subsidies, investor incentives).
        
        Return ONLY a JSON object with two integer scores (0-10) for each category.
        Format: {{"austerity_score": int, "extravagance_score": int}}
        
        TEXT:
        {sample}
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/CommonerLLP/budget-crawler",
            "X-Title": "CommonerLLP OBI Engine"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            if 'choices' not in result:
                print(f"  DEBUG: OpenRouter Error Response: {result}")
                return {"error": "Invalid API Response", "austerity_score": 0, "extravagance_score": 0, "provider": "openrouter:error"}

            content = result['choices'][0]['message']['content']
            data = json.loads(content)
            data["provider"] = f"openrouter:{self.model}"
            
            # Diagnostic print for the first successful run
            print(f"  DEBUG: LLM Response for signals: {data}")
            
            return data
        except Exception as e:
            return {"error": str(e), "austerity_score": 0, "extravagance_score": 0, "provider": "openrouter:error"}

def get_provider(provider_type, **kwargs):
    if provider_type == "ollama":
        return OllamaProvider(**kwargs)
    elif provider_type == "openrouter":
        return OpenRouterProvider(**kwargs)
    return RegexProvider()
