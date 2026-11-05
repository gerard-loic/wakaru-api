from custom.libs.modelhelper import ModelHelper
from custom.libs.mediahelper import MediaHelper
from custom.libs.traininghelper import TrainingHelper
from app.crud.model import get_model
from app.exceptions import ApiError
from app.mail.service import get_mail_service
from sqlalchemy import select
from sqlalchemy.orm import Session
import logging
import json

#Seuls les utilisateurs de ce rôle reçoivent les user_knowledge d'une nouvelle leçon
LESSON_ROLE_UID = "USERTEST"

def themeMailContext(theme)->dict:
    """Variables du gabarit `new_theme` pour une ligne de `themes`."""
    return {
        "theme_name" : theme.name,
        "theme_description" : theme.description,
        "theme_image" : theme.image,
        "image_credit" : theme.image_credit,
        "image_licence" : theme.image_licence
    }

class LLMHelper:
    def __init__(self, db: Session, llmData:dict):
        self._db = db
        self._model = ModelHelper(db)
        self._data = llmData
        self._logger = logging.getLogger("sylo_api.llmhelper")
        self._level_id = 1
        self._theme_id = 1

    #--------------------------------------------------------------------------------
    #Méthode principale d'import

    def importData(self)->dict:
        out = {}

        #Import du thème
        out["theme"] = self._importTheme()

        #Import du kanji
        out["kanji"] = self._importKanji()

        #Import du vocabulaire
        out["words"] = self._importWords()

        #Import de la règle de grammaire
        out["grammar"] = self._importGrammar()

        #Import des phrases
        out["sentences"] = self._importSentences()

        #Import des exercices
        out["exercises"] = self._importExercises()
    
        #Activation (user knowledge)
        self._model.initUsers(entity_name="theme", entity_id=out["theme"], level_id=self._level_id, role_uid=LESSON_ROLE_UID)
        self._model.initUsers(entity_name="kanji", entity_id=out["kanji"], level_id=self._level_id, role_uid=LESSON_ROLE_UID)
        for w in out["words"]:
            self._model.initUsers(entity_name="word", entity_id=w, level_id=self._level_id, role_uid=LESSON_ROLE_UID)
        self._model.initUsers(entity_name="grammar_rule", entity_id=out["grammar"], level_id=self._level_id, role_uid=LESSON_ROLE_UID)
        for s in out["sentences"]:
            self._model.initUsers(entity_name="sentence", entity_id=s, level_id=self._level_id, role_uid=LESSON_ROLE_UID)
        for e in out["exercises"]:
            self._model.initUsers(entity_name="exercise", entity_id=e, level_id=self._level_id, role_uid=LESSON_ROLE_UID)

        #Programme de la semaine : dépend des user_knowledge créés ci-dessus
        TrainingHelper.initThemeProgram(self._db, out["theme"])

        
        
        return out

    

    def notifyUsers(self, theme_id:int)->None:
        """
        Annonce le thème aux utilisateurs qui l'ont reçu à l'import (gabarit `new_theme`,
        sujet préfixé par [Test]). À appeler après le commit de l'import. Un échec est
        journalisé et n'interrompt pas les envois suivants.
        """
        themes = get_model("theme").table
        users = get_model("user").table
        knowledges = get_model("user_knowledge").table

        theme = self._db.execute(select(themes).where(themes.c.id == theme_id)).first()
        recipients = self._db.execute(
            select(users.c.email, users.c.first_name)
            .where(
                users.c.deleted_at.is_(None),
                users.c.id.in_(
                    select(knowledges.c.user_id).where(
                        knowledges.c.entity_name == "theme",
                        knowledges.c.entity_id == theme_id,
                        knowledges.c.deleted_at.is_(None)
                    )
                )
            )
            .order_by(users.c.id)
        ).all()

        mail_service = get_mail_service()
        for email, first_name in recipients:
            try:
                mail_service.send(
                    self._db,
                    to=email,
                    template="new_theme",
                    context={**themeMailContext(theme), "name" : first_name, "is_test" : True}
                )
            except ApiError as e:
                #error : le logger sylo_api ignore les niveaux inférieurs
                self._logger.error("Mail du thème %s non envoyé à %s : %s", theme_id, email, e.message)

    #--------------------------------------------------------------------------------
    #Méthodes getter (publiques)

    def getTheme(self)->dict:
        return self._data["theme"]

    def getKanji(self)->dict:
        return self._data["kanji"]

    def getWords(self)->list:
        return self._data["words"]

    def getGrammar(self)->dict:
        return self._data["grammar"]

    def getSentences(self)->list:
        return self._data["sentences"]

    def getExercises(self)->list:
        return self._data["exercises"]

    #--------------------------------------------------------------------------------
    #Méthodes d'import (privées)

    def _importTheme(self)->int:
        t = self.getTheme()

        #Téléchargement de l'image, stockée localement et servie publiquement
        image = None
        if t.get("image"):
            try:
                image = MediaHelper().downloadImage(t["image"], subdir="themes")
            except Exception as e:
                #error : le logger sylo_api ignore les niveaux inférieurs
                self._logger.error("Image du thème non importée (%s) : %r", t["image"], e)

        theme_id = self._model.create(
            table="themes",
            data={
                "name" : t["name"],
                "description" : t["description"],
                "image_credit" : t["image_credit"],
                "image_licence" : t["image_licence"],
                "image" : image
            }
        )
        self._theme_id = theme_id
        return theme_id

    def _importKanji(self)->int:
        k = self.getKanji()
        id, _ = self._model.getOrCreate(
            table="kanjis",
            attribute="char",
            value = k["char"],
            data = {
                "char" : k["char"],
                "readings" : json.dumps(k["readings"]),
                "description" : k["description"],
                "translations" : json.dumps(k["translations"]),
                "level_id" : self._level_id,
                "strokes" : k["strokes"],
                "radical" : k["radical"],
                "grade" : k["grade"],
                "unicode" : k["unicode"]
            }
        )
        self._model.link(
            table="theme_kanji",
            data={
                "kanji_id" : id,
                "theme_id" : self._theme_id
            }
        )

        #Je recherche les compositions qui contiennent ce kanji
        compo_ids = self._model.get(
            table="compositions",
            attribute="text",
            value=k["char"],
            multiple=True,
            contains=True
        )
        for c in compo_ids:
            #Par compo, mettre à jour la liaison
            self._model.link(
                table="composition_kanji",
                data={
                    "composition_id" : c,
                    "kanji_id" : id
                }
            )

        return id

    def _importWords(self)->list:
        out = []

        words_id = self.getWords()

        for w in words_id:
            out.append(self._importWord(w))

        return out

    def _importWord(self, w:dict):
        uid = self._getWordUid(writing=w["writing"], reading=w["reading"])
        #if w["pos"] in ["verb_godan","verb_ichidan","verb_irregular"]:
        #    uid = self._getWordUid(writing=w["writing"], reading=w["reading"], lemma=w["reading"])

        #Get pos
        pos_id = self._model.get(
            table="partofspeeches",
            attribute="uid",
            value=w["pos"]
        )
        #TODO : pos_id is NULL

        #examples
        examples = []
        if "examples" in w:
            examples = w["examples"]

        #Description
        description = ""
        if "description" in w:
            description = w["description"]

        id, created = self._model.getOrCreate(
            table="words",
            attribute="uid",
            value=uid,
            data={
                "uid" : uid,
                "writing" : w["writing"],
                "reading" : w["reading"],
                "partofspeech_id" : pos_id,
                "translations" : json.dumps(w["translations"]),
                "description" : description,
                "examples" : json.dumps(examples),
                "level_id" : self._level_id
            }
        )

        #Si creation, ajout des compositions
        if created is True and "composition" in w:
            for c in w["composition"]:
                #Get type
                type_id = self._model.get(
                    table="composition_types",
                    attribute="uid",
                    value=c["type"]
                )
                #TODO : type_id is NONE

                #Determination rendaku
                is_rendaku = False
                if "rendaku" in c and c["rendaku"] == True:
                    is_rendaku = True

                #Ajout de la composition
                comp_id = self._model.create(
                    table="compositions",
                    data={
                        "text" : c["text"],
                        "reading" : c["reading"],
                        "word_id" : id,
                        "composition_type_id" : type_id,
                        "is_rendaku" : is_rendaku
                    }
                )

                #Liaison de la composition aux kanjis
                for char in c["text"]:
                    kanji_id = self._model.get(
                        table="kanjis",
                        attribute="char",
                        value=char
                    )
                    if kanji_id is not None:
                        self._model.link(
                            table="composition_kanji",
                            data={
                                "composition_id" : comp_id,
                                "kanji_id" : kanji_id
                            }
                        )

        #Ajout du mot à la lesson
        self._model.create(
            table="theme_words",
            data={
                "theme_id" : self._theme_id,
                "word_id" : id,
                "role" : w["role"]
            }
        )

        #Liaison du mot à des parties de phrase
        sentence_token_ids = self._model.get(
            table="sentence_tokens",
            attribute="word_uid",
            value=uid,
            multiple=True
        )
        for t in sentence_token_ids:
            self._model.update(
                table="sentence_tokens",
                id=t,
                data={
                    "word_id" : id
                }
            )

        return id

    def _importGrammar(self)->id:
        g = self.getGrammar()

        #Get category
        category_id = self._model.get(
            table="grammar_categories",
            attribute="uid",
            value=g["category"]
        )
        #TODO : id category_id IS NONE

        id = self._model.create(
            table="grammar_rules",
            data={
                "uid" : g["uid"],
                "name" : g["name"],
                "description" : g["description"],
                "grammar_category_id" : category_id,
                "theme_id" : self._theme_id,
                "level_id" : self._level_id
            }
        )
        return id

    def _importSentences(self)->list:
        out = []
        sentences = self.getSentences()
        for s in sentences:
            out.append(self._importSentence(s))

        return out


    def _importSentence(self, s:dict)->int:
        id = self._model.create(
            table="sentences",
            data={
                "text" : s["text"],
                "theme_id" : self._theme_id,
                "level_id" : self._level_id,
                "translation" : s["translation"]
            }
        )

        #Ajout des tokens
        for t in s["tokens"]:
            #Preparation des attributs
            reading = t["text"]
            if "reading" in t:
                reading = t["reading"]
            lemma = ""
            if "lemma" in t:
                lemma = t["lemma"]


            if "word_uid" in t:
                word_uid = t["word_uid"]
            else:
                word_uid = self._getWordUid(writing=t["text"], reading=reading)
                if lemma != "":
                    word_uid = self._getWordUid(writing=t["text"], reading=reading, lemma=lemma)

            #Chercher le mot
            word_id = self._model.get(
                table="words",
                attribute="uid",
                value=word_uid
            )

            #Rôle du mot
            role = ""
            if "role" in t:
                role = t["role"]
            sentence_token_role_id = self._model.get(
                table="sentence_token_roles",
                attribute="uid",
                value=role
            )

            self._model.create(
                table="sentence_tokens",
                data={
                    "sentence_id" : id,
                    "text" : t["text"],
                    "reading" : reading,
                    "lemma" : lemma,
                    "word_id" : word_id,
                    "sentence_token_role_id" : sentence_token_role_id,
                    "word_uid" : word_uid
                }
            )
        return id

    def _importExercises(self)->list:
        out = []
        exercises = self.getExercises()
        for e in exercises:
            out.append(self._importExercise(e))
        return out

    def _importExercise(self, e:dict)->int:
        category_id = self._model.get(
            table="exercise_categories",
            attribute="uid",
            value=e["category"]
        )
        #TODO : category_id IS NULL

        type_id = self._model.get(
            table="exercise_types",
            attribute="uid",
            value=e["type"]
        )
        #TODO : type_id IS NULL

        id = self._model.create(
            table="exercises",
            data={
                "exercise_category_id" : category_id,
                "exercise_type_id" : type_id,
                "level_id" : self._level_id,
                "theme_id" : self._theme_id,
                "name" : e["name"],
                "instructions" : e["instructions"],
                "choices" : json.dumps(e["choices"])
            }
        )

        for i in e["items"]:
            self._importExerciseItem(id, i)

        return id

    def _importExerciseItem(self, exercise_id:int, i:dict)->int:
        id = self._model.create(
            table="exercise_items",
            data={
                "exercise_id" : exercise_id,
                "prompt" : i["prompt"],
                "translation" : i["translation"],
                "blanks" : json.dumps(i["blanks"]),
                "explanation" : i["explanation"]
            }
        )


    #--------------------------------------------------------------------------------
    #Méthodes utils

    def _getWordUid(self, writing:str, reading:str, lemma:str=None)->str:
        if lemma:
            return lemma
        return writing+":"+reading

    #--------------------------------------------------------------------------------------------------------
    

   