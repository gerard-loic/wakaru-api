from sqlalchemy.orm import Session
from custom.libs.llmhelper import LLMHelper, ModelHelper
from custom.libs.trainingconf import TRAININGCONF

def stats_items_method(db: Session, user_id:int) -> dict:
    
    out = {}

    model = ModelHelper(db)

    #Les proportions portent sur les mêmes mots que l'entraînement (partofspeech.is_worked_on)
    word_filters = TRAININGCONF["words"]["item_filters"]
    out["words"] = {
        "all" : model.count(table="words", user_id=user_id),
        "new" : model.count(table="words", user_id=user_id, only_new=True),
        "worked_on" : model.countKnown(table="words", user_id=user_id, filters=word_filters),
        "proportions" : model.knowledgeProportions(table="words", user_id=user_id, filters=word_filters)
    }
    out["hiraganas"] = {
        "all" : model.count(table="hiraganas", user_id=user_id),
        "new" : model.count(table="hiraganas", user_id=user_id, only_new=True),
        "proportions" : model.knowledgeProportions(table="hiraganas", user_id=user_id)
    }
    out["katakanas"] = {
        "all" : model.count(table="katakanas", user_id=user_id),
        "new" : model.count(table="katakanas", user_id=user_id, only_new=True),
        "proportions" : model.knowledgeProportions(table="katakanas", user_id=user_id)
    }
    out["themes"] = {
        "all" : model.count(table="themes", user_id=user_id),
        "new" : model.count(table="themes", user_id=user_id, only_new=True)
    }
    out["kanjis"] = {
        "all" : model.count(table="kanjis", user_id=user_id),
        "new" : model.count(table="kanjis", user_id=user_id, only_new=True),
        "proportions" : model.knowledgeProportions(table="kanjis", user_id=user_id)
    }
    out["grammar_rules"] = {
        "all" : model.count(table="grammar_rules", user_id=user_id),
        "new" : model.count(table="grammar_rules", user_id=user_id, only_new=True)
    }
    out["sentences"] = {
        "all" : model.count(table="sentences", user_id=user_id),
        "new" : model.count(table="sentences", user_id=user_id, only_new=True),
        "proportions" : model.knowledgeProportions(table="sentences", user_id=user_id)
    }
    out["exercises"] = {
        "all" : model.count(table="exercises", user_id=user_id),
        "new" : model.count(table="exercises", user_id=user_id, only_new=True),
        "proportions" : model.knowledgeProportions(table="exercises", user_id=user_id)
    }

    return out
