from sqlalchemy.orm import Session
from custom.libs.llmhelper import LLMHelper

def create_lesson(db: Session, data: dict) -> dict:
    
    llm = LLMHelper(db=db, llmData=data)


    out = llm.importData()
    db.commit()


    return out
