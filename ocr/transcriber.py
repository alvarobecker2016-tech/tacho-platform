import base64
from typing import List, Tuple
from pydantic import BaseModel
from openai import OpenAI
from domain.enums import EventType

client = OpenAI()

class OCRTimelineEvent(BaseModel):
    start_time_raw: str
    duration_raw: str
    pictogram_raw: str

class OCRExtractionResult(BaseModel):
    document_date: str
    events: List[OCRTimelineEvent]

class OCRTranscriber:
    def extract(self, image_bytes) -> Tuple[str, List[OCRTimelineEvent]]:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        prompt = "Extract timeline from tachograph receipt. Read each row exactly as printed. Extract 'start_time_raw' (HH:MM), 'duration_raw' (HHhMM), and 'pictogram_raw' (the exact symbol like *, o, h, X). Stop at '--- Σ ---'."
        
        res = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}
            ],
            response_format=OCRExtractionResult,
            temperature=0
        )
        
        parsed = res.choices[0].message.parsed
        return parsed.document_date, parsed.events
