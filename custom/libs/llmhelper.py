from custom.libs.modelhelper import ModelHelper
from sqlalchemy.orm import Session
import logging


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
        t = self.getTheme()
        theme_id = self._model.create(
            table="themes",
            data={
                "name" : t["name"],
                "description" : t["description"]
            }
        )
        out["theme"] = theme_id
        self._theme_id = theme_id

        #Import du vocabulaire
        out["words"] = self._importVocabulary()

        #Import du Kanji
        out["kanji"] = self._importKanji()

        #Import des mots kanjis
        out["kanjiwords"] = self._importKanjiCompositions()
        
        #Import règle de grammaire
        out["grammar_rule"] = self._importGrammarRule()

        #Import 

        #Activation (user knowledge)
        for w in out["words"]:
            self._model.initUsers(entity_name="word", entity_id=w, level_id=self._level_id)
        self._model.initUsers(entity_name="kanji", entity_id=out["kanji"], level_id=self._level_id)
        self._model.initUsers(entity_name="grammar_rule", entity_id=out["grammar_rule"], level_id=self._level_id)

        return out


    #--------------------------------------------------------------------------------
    #Méthodes getter (publiques)

    def getTheme(self)->dict:
        return self._data["theme"]

    def getVocabulary(self)->list:
        return self._data["vocabulary"]

    def getKanji(self)->dict:
        return self._data["kanji"]

    def getGrammarRule(self)->dict:
        return self._data["grammar_rules"]

    def getKanjiCompositions(self)->list:
        return self._data["kanjiwords"]

    #--------------------------------------------------------------------------------
    #Méthodes d'import (privées)


    def _importKanji(self)->int:
        k = self.getKanji()
        id, _ = self._model.getOrCreate(
            table="kanjis",
            attribute="kanji",
            value = k["kanji"],
            data = {
                "kanji" : k["kanji"],
                "on_reading" : k["onreading"],
                "kun_reading" : k["kunreading"],
                "description" : k["description"],
                "translations" : k["translations"],
                "level_id" : self._level_id,
                "strokes" : k["strokes"],
                "radical" : k["radical"],
                "jlpt" : k["jlpt"],
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

        #Mise à jour des compositions utilisant ce kanji
        compo_ids = self._model.get(
            table="kanji_compositions",
            attribute="kanji",
            value=k["kanji"],
            multiple=True
        )
        for c in compo_ids:
            self._model.update(
                table="kanji_compositions",
                id=c,
                data={
                    "kanji_id" : id
                }
            )

        return id

    def _importKanjiCompositions(self)->list:
        out = []

        for d in self.getKanjiCompositions():
            kanjiword_id, creation = self._model.getOrCreate(
                table="kanjiwords",
                attribute="writing",
                value=d["writing"],
                data={
                    "writing" : d["writing"],
                    "reading" : d["reading"],
                    "translations" : d["translations"]
                }
            )
            out.append(kanjiword_id)
            if creation:
                #Creation des liaisons compo / kanji
                for c in d["composition"]:
                    #On regarde si le kanji de la composition existe
                    kanji_id = self._model.get(
                        table="kanjis",
                        attribute="kanji",
                        value=c["kanji"]
                    )

                    if kanji_id is None:
                        #Pas de kanji existant associé
                        self._model.create(
                            table="kanji_compositions",
                            data={
                                "kanjiword_id" : kanjiword_id,
                                "reading" : c["reading"],
                                "type" : c["type"],
                                "kanji" : c["kanji"]
                            }
                        )
                    else:
                        #Kanji associé
                        self._model.create(
                            table="kanji_compositions",
                            data={
                                "kanji_id" : kanji_id,
                                "kanjiword_id" : kanjiword_id,
                                "reading" : c["reading"],
                                "type" : c["type"],
                                "kanji" : c["kanji"]
                            }
                        )
        return out




    
    def _importVocabulary(self)->list:
        out = []
        for v in self.getVocabulary():
            word_id, _ = self._model.getOrCreate(
                table="words",
                attribute="japanese",
                value=v["japanese"],
                data={
                    "japanese" : v["japanese"],
                    "translation" : v["translation"],
                    "description" : v["description"],
                    "level_id" : self._level_id
                }
            )
            self._model.link(
                table="theme_word",
                data={
                    "word_id" : word_id,
                    "theme_id" : self._theme_id
                }
            )
            out.append(word_id)

        return out  

    def _importGrammarRule(self)->int:
        g = self.getGrammarRule()
        id = self._model.create(
            table="grammar_rules",
            data={
                "name" : g["name"],
                "description" : g["description"],
                "category_id" : g["category"],
                "theme_id" : self._theme_id,
                "level_id" : self._level_id
            }
        )
        return id
