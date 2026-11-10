from sqlalchemy.orm import Session
from custom.libs.traininghelper import TrainingHelper

def new_training_method(db: Session, user_id:int, subject:str, element_from:str, element_to:list, focus:str, number:int|None=None) -> dict:

    t = TrainingHelper(
        db=db,
        user_id=user_id,
        subject=subject,
        element_from=element_from,
        element_to=element_to,
        number=number,
        focus=focus
    )
    out = t.getTraining()

    return out

def get_configuration_method(db: Session, user_id:int) -> dict:
    return TrainingHelper.getConfiguration(db=db, user_id=user_id)