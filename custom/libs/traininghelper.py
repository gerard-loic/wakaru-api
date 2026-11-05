
from custom.libs.modelhelper import ModelHelper, resolve_model
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session
import random
import json
import logging
from custom.libs.trainingconf import TRAININGCONF

#Nombre minimum d'éléments pour proposer un sujet ou un focus
MIN_ITEMS = 5

#Sujets tirés au hasard par le mode mix
MIX_SUBJECTS = ["words", "hiraganas", "katakanas", "kanjis", "sentences"]

#Programme d'un thème : nombre de jours, sujets d'entraînement et type "exercice du thème"
PROGRAM_DAYS = 7
PROGRAM_SUBJECTS = ["words", "katakanas", "hiraganas", "sentences", "kanjis"]
PROGRAM_EXERCISES_TYPE = "exercises"


class _TrainingSettings(BaseSettings):
    """Paramètres des entraînements, lus dans le `.env` du projet (préfixe `WAKARU_`)."""

    # Nombre d'exercices proposés chaque jour dans le programme d'un thème.
    program_exercises_per_day: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WAKARU_", extra="ignore")


_training_settings = _TrainingSettings()


class TrainingHelper:

    def getConfiguration(db: Session, user_id:int)->dict:
        model = ModelHelper(db)
        out = {"subjects" : []}
        for subject in TRAININGCONF:
            api = TRAININGCONF[subject]["api"]

            #Le sujet kanjis n'est proposé qu'à partir de MIN_ITEMS kanjis connus
            if subject == "kanjis" and TrainingHelper._countKnown(model, user_id, subject, "random") < MIN_ITEMS:
                continue

            #Le focus weakness n'est proposé qu'à partir de MIN_ITEMS éléments à revoir
            focus = [
                f for f in api["focus"]
                if f["focus"] != "weakness" or TrainingHelper._countKnown(model, user_id, subject, "weakness") >= MIN_ITEMS
            ]
            out["subjects"].append({**api, "focus" : focus})

        return out

    def _countKnown(model:ModelHelper, user_id:int, subject:str, focus:str)->int:
        conf = TRAININGCONF[subject]
        return model.countKnown(table=subject, user_id=user_id, focus=focus, filters=conf["item_filters"])

    def getThemeProgram(db: Session, user_id:int, theme_id:int, per_day:int|None = None)->dict:
        """
        Génère le programme de `user_id` sur le thème `theme_id` : un dict
        {"day1" : [...], ..., "day7" : [...]}, chaque jour listant `per_day` exercices
        (par défaut WAKARU_PROGRAM_EXERCISES_PER_DAY) tous différents.

        Le type est tiré au hasard, puis un exercice de ce type. Un jour compte moins
        de `per_day` exercices s'il n'y a pas assez de combinaisons disponibles.

        Rien n'est écrit en base. Les `user_knowledge` du thème doivent déjà exister :
        ils déterminent ce qui est possible pour l'utilisateur.
        """
        if per_day is None:
            per_day = _training_settings.program_exercises_per_day

        candidates = TrainingHelper._getProgramCandidates(db, user_id, theme_id)

        out = {}
        for day in range(1, PROGRAM_DAYS + 1):
            #Tirage sans remise : deux exercices identiques sont impossibles le même jour
            remaining = {type_ : list(items) for type_, items in candidates.items()}
            out[f"day{day}"] = []
            while remaining and len(out[f"day{day}"]) < per_day:
                type_ = random.choice(list(remaining))
                items = remaining[type_]
                out[f"day{day}"].append({**items.pop(random.randrange(len(items))), "done" : False})
                if not items:
                    del remaining[type_]

        return out

    def initThemeProgram(db: Session, theme_id:int, user_id:int|None = None)->None:
        """
        Stocke le programme du thème dans `details` des `user_knowledge` de `theme_id`
        (uniquement celui de `user_id` s'il est fourni). À appeler une fois tous les
        `user_knowledge` du thème créés. Les lignes ayant déjà un programme ne sont pas
        modifiées. Ne commit pas : au caller de valider la transaction.
        """
        uk = resolve_model("user_knowledge").python_class
        query = select(uk).where(
            uk.entity_name == resolve_model("theme").name,
            uk.entity_id == theme_id,
            uk.details.is_(None),
            uk.deleted_at.is_(None)
        )
        if user_id is not None:
            query = query.where(uk.user_id == user_id)

        for knowledge in db.execute(query).scalars().all():
            program = TrainingHelper.getThemeProgram(db, knowledge.user_id, theme_id)
            knowledge.details = json.dumps(program, ensure_ascii=False)
        db.flush()

    def _getProgramCandidates(db: Session, user_id:int, theme_id:int)->dict:
        """
        Retourne les exercices réalisables par `user_id` sur ce thème, groupés par type.
        Les types sans exercice réalisable sont absents.
        """
        model = ModelHelper(db)
        out = {}

        for api in TrainingHelper.getConfiguration(db, user_id)["subjects"]:
            subject = api["subject"]
            if subject not in PROGRAM_SUBJECTS:
                continue

            #Un focus sans élément ferait échouer l'entraînement (ex. thème sans phrase)
            focus = [f for f in api["focus"] if TrainingHelper._countKnown(model, user_id, subject, f["focus"]) > 0]

            items = [
                {
                    "type" : subject,
                    "element_from" : m["element_from"],
                    "element_to" : m["element_to"],
                    "focus" : f["focus"],
                    "name" : TRAININGCONF[subject]["program_names"][f["focus"]]
                }
                for m in api["modes"] for f in focus
            ]
            if items:
                out[subject] = items

        exercises = model.getKnown(table="exercises", user_id=user_id, filters={"theme_id" : theme_id})
        if exercises:
            out[PROGRAM_EXERCISES_TYPE] = [
                {"type" : PROGRAM_EXERCISES_TYPE, "name" : e.name, "exercise_id" : e.id}
                for e in exercises
            ]

        return out

    def __init__(self, db: Session, user_id:int, subject:str, element_from:str, element_to:list, number:int, focus:str):
        """
        Subjects : words, hiraganas, katakanas, kanjis, sentences, mix
        element_from : char, reading, french, char_or_reading (mix)
        element_to : char, reading, french, char_or_reading (mix)
        focus : theme, weakness, random
                
        """
        
        self._db = db
        self._user_id = user_id
        self._model = ModelHelper(db)
        self._logger = logging.getLogger("sylo_api.traininghelper")

        #Vérification des conformités
        if subject not in ["words","hiraganas","katakanas","kanjis","sentences","mix"]:
            raise Exception(f"Subject {subject} not supported")
        
        if element_from not in ["char", "reading", "french", "char_or_reading"]:
            raise Exception(f"Element_from {element_from} not supported")
        
        for et in element_to:
            if et not in ["char", "reading", "french", "char_or_reading"]:
                raise Exception(f"Element_to {et} not supported")

        conf = TrainingHelper.getConfiguration(db, user_id)
        subject_found = False
        focus_found = False
        element_from_found = False
        element_to_found = False
        for c in conf["subjects"]:
            if c["subject"]==subject:
                self._logger.error("subject OK")
                subject_found = True
                for f in c["focus"]:
                    if f["focus"]==focus:
                        self._logger.error("focus OK")
                        focus_found = True
                for m in c["modes"]:
                    if m["element_from"]==element_from and all(x in element_to for x in m["element_to"]):
                        self._logger.error("elements OK")
                        element_from_found = True
                        element_to_found = True
        if subject_found==False:
            raise Exception(f"Configuration non valid : sujet '{subject}' non disponible")
        if focus_found==False:
            raise Exception(f"Configuration non valid : focus '{focus}' non disponible pour '{subject}'")
        if element_to_found==False or element_from_found==False:
            raise Exception(f"Configuration non valid : mode {element_from} -> {element_to} non disponible pour '{subject}'")
                        


        
        self._subject = subject
        self._element_from = element_from
        self._element_to = element_to
        self._number = number
        self._focus = focus

        #Sujets du mix compatibles avec les éléments demandés et disponibles pour l'utilisateur
        if subject == "mix":
            self._mix_subjects = [
                s for s in MIX_SUBJECTS
                if self._resolveElements(TRAININGCONF[s], element_from, element_to) is not None
                and TrainingHelper._countKnown(self._model, user_id, s, focus) >= (MIN_ITEMS if s == "kanjis" else 1)
            ]
            if not self._mix_subjects:
                raise Exception("Aucun sujet disponible pour ce mode")


    def getTraining(self)->dict:
        self._out = {
            "items" : []
        }

        for i in range(self._number):
            self._out["items"].append(self._getTrainingItem2())

        return self._out

    def _getTrainingItem2(self)->dict:
        #Finaliser le sujet
        subject = self._subject
        if subject == "mix":
            subject = random.choice(self._mix_subjects)

        #Recupérer le configuration à utiliser
        conf = TRAININGCONF[subject]

        #Résoudre char_or_reading selon les modes du sujet
        element_from, element_to = self._resolveElements(conf, self._element_from, self._element_to)

        #Récupérer l'item principal
        subject_item = self._model.getRandom(
            table=subject,
            user_id=self._user_id,
            focus=self._focus,
            load=conf["item_relations"],
            filters=conf["item_filters"]
        )
        if subject_item is None:
            raise Exception(f"Aucun élément '{subject}' disponible pour l'utilisateur avec le focus '{self._focus}'")

        #Préparer ce qui s'affiche à l'écran pour la question (le texte)
        mode_question = self._getModeFromConf(conf=conf, element_from=element_from, element_to=element_to[0])
        question_text = self._getAttributeValue(
            item=subject_item,
            attribute=mode_question["question.text.attribute"],
            list_item=mode_question["question.text.attribute.listitem"]
        )
        question_reading = self._getAttributeValue(
            item=subject_item,
            attribute=mode_question["question.reading.attribute"],
            list_item=mode_question["question.reading.attribute.listitem"]
        )

        #Préparer la sortie
        out = {
            "entity" : subject,
            "id" : subject_item["id"],
            "text" : question_text,
            "reading" : "",
            "questions" : [],
            "user_knowledge" : subject_item["user_knowledge"]["id"]
        }
        if question_reading != question_text:
            out["reading"] = question_reading

        
        #Préparer les questions
        for elmt_to in element_to:
            mode_answer = self._getModeFromConf(conf=conf, element_from=element_from, element_to=elmt_to)
            q_out = {
                "to" : elmt_to,
                "instructions" : mode_answer["question.instructions"],
                "propositions" : []
            }

            ids = [subject_item["id"]]
            for i in range(3):
                proposition_item = self._model.getRandom(
                    table=subject,
                    user_id=self._user_id,
                    focus="random",
                    avoid_ids=ids,
                    load=conf["item_relations"],
                    filters=conf["item_filters"]
                )
                #Pas assez d'éléments connus pour 3 propositions
                if proposition_item is None:
                    break

                p_out = {
                    "id" : proposition_item["id"],
                    "text" : self._getAttributeValue(
                        item=proposition_item,
                        attribute=mode_answer["answer.text.attribute"],
                        list_item=mode_answer["answer.text.attribute.listitem"]
                    ),
                    "reading" : ""
                }
                reading = self._getAttributeValue(
                    item=proposition_item,
                    attribute=mode_answer["answer.reading.attribute"],
                    list_item=mode_answer["answer.reading.attribute.listitem"]
                )
                if reading != p_out["text"]:
                    p_out["reading"] = reading
                ids.append(proposition_item["id"])
                q_out["propositions"].append(p_out)

            p_out = {
                "id" : subject_item["id"],
                "text" : self._getAttributeValue(
                    item=subject_item,
                    attribute=mode_answer["answer.text.attribute"],
                    list_item=mode_answer["answer.text.attribute.listitem"]
                ),
                "reading" : ""
            }
            reading = self._getAttributeValue(
                item=subject_item,
                attribute=mode_answer["answer.reading.attribute"],
                list_item=mode_answer["answer.reading.attribute.listitem"]
            )
            if reading != p_out["text"]:
                p_out["reading"] = reading

            q_out["propositions"].append(p_out)
            random.shuffle(q_out["propositions"])
                    
            out["questions"].append(q_out)

        return out
        


    def _resolveElements(self, conf:dict, element_from:str, element_to:list)->tuple|None:
        """
        Remplace char_or_reading par char, ou à défaut reading, selon les modes
        configurés pour le sujet. Retourne None si aucun mode ne correspond.
        """
        def candidates(element:str)->list:
            return ["char", "reading"] if element == "char_or_reading" else [element]

        def has_mode(e_from:str, e_to:str)->bool:
            return any(m["element_from"] == e_from and m["element_to"] == e_to for m in conf["modes"])

        for e_from in candidates(element_from):
            resolved_to = []
            for et in element_to:
                e_to = next((c for c in candidates(et) if has_mode(e_from, c)), None)
                if e_to is None:
                    break
                resolved_to.append(e_to)
            else:
                return e_from, resolved_to
        return None

    def _getModeFromConf(self, conf:dict, element_from:str, element_to:str)->dict:
        for m in conf["modes"]:
            if m["element_from"] == element_from and m["element_to"] == element_to:
                return m
        raise Exception(f"No mode configured from {element_from} to {element_to}")

    def _getAttributeValue(self, item:dict, attribute:str, list_item)->str:
        if attribute is None:
            return ""
        if list_item is None:
            return item[attribute]
        return json.loads(item[attribute])[list_item]

    def _getTrainingItem(self)->dict:
        subject = self._subject
        if subject == "mix":
            subject = random.choice(["words", "hiraganas", "katakanas", "kanjis", "sentences"])

        subject_item = self._model.getRandom(
            table=subject,
            user_id=self._user_id,
            focus=self._focus,
            load=["partofspeech"],
            filters={
                "partofspeech.is_worked_on" : True
            }
        )

        item_data = {}
        if subject == "words":
            item_data = self._getPrepareWordItem(subject_item=subject_item)
        elif subject == "hiraganas":
            item_data = self._getPrepareHiraganaItem(subject_item=subject_item)
        elif subject == "katakanas":
            item_data = self._getPrepareKatakanaItem(subject_item=subject_item)
        elif subject == "kanjis":
            item_data = self._getPrepareKanjiItem(subject_item=subject_item)
        elif subject == "sentences":
            item_data = self._getPrepareSentenceItem(subject_item=subject_item)

        return item_data

    def _getPreparedItem(self, subject_item:dict, subject:str)->dict:
        conf = _CONF[subject]

        #Preparer l'item sur lequel il y aura des questions
        item = ""
        if self._element_from == "char":
            item = subject_item[conf["text_attribute"]]
        elif self._element_from == "french":
            item = json.loads(subject_item["translations"])[0]


    def _getPrepareWordItem(self, subject_item:dict)->dict:
        

        #Preparer l'item sur lequel il y aura des questions
        item = ""
        if self._element_from == "char":
            item = subject_item["writing"]
        elif self._element_from == "french":
            item = json.loads(subject_item["translations"])[0]

        out = {
            "entity" : "words",
            "id" : subject_item["id"],
            "text" : item,
            "questions" : []
        }

        #Préparer les questions
        for elmt_to in self._element_to:
            q_out = {
                "to" : elmt_to,
                "propositions" : []
            }

            props = []
            ids = [subject_item["id"]]
            for i in range(3):
                proposition_item = self._model.getRandom(
                    table="words",
                    user_id=self._user_id,
                    focus="random",
                    avoid_ids=ids,
                    load=["partofspeech"],
                    filters={
                        "partofspeech.is_worked_on" : True
                    }
                )
                text = ""
                if elmt_to == "char":
                    text = proposition_item["writing"]
                elif elmt_to == "reading":
                    text = proposition_item["reading"]
                elif elmt_to == "french":
                    text = json.loads(proposition_item["translations"])[0]

                p_out = {
                    "id" : proposition_item["id"],
                    "text" : text
                }
                ids.append(proposition_item["id"])
                q_out["propositions"].append(p_out)

            
            text = ""
            if elmt_to == "char":
                text = subject_item["writing"]
            elif elmt_to == "reading":
                text = subject_item["reading"]
            elif elmt_to == "french":
                text = json.loads(subject_item["translations"])[0]

            p_out = {
                "id" : subject_item["id"],
                "text" : text
            }
            q_out["propositions"].append(p_out)
            random.shuffle(q_out["propositions"])
            
            out["questions"].append(q_out)

        return out



    def _getPrepareHiraganaItem(self, subject_item:dict)->dict:
        pass

    def _getPrepareKatakanaItem(self, subject_item:dict)->dict:
        pass

    def _getPrepareKanjiItem(self, subject_item:dict)->dict:
        pass

    def _getPrepareSentenceItem(self, subject_item:dict)->dict:
        pass

