TRAININGCONF = {
    "words" : {
        "program_names" : {
            "theme" : "Travailler le vocabulaire du thème",
            "weakness" : "Travailler le vocabulaire difficile",
            "random" : "Travailler du vocabulaire au hasard"
        },
        "item_relations" : ["partofspeech"],
        "item_filters" : {
            "partofspeech.is_worked_on" : True
        },
        "modes" : [
            {
                "element_from" : "char",
                "element_to" : "french",
                "question.text.attribute" : "writing",
                "question.text.attribute.listitem" : None,
                "question.reading.attribute" : "reading",
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "translations",
                "answer.text.attribute.listitem" : 0,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Quelle est la signification de ce mot ?"
            },
            {
                "element_from" : "french",
                "element_to" : "char",
                "question.text.attribute" : "translations",
                "question.text.attribute.listitem" : 0,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "writing",
                "answer.text.attribute.listitem" : None,
                "answer.reading.attribute" : "reading",
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Comment ce mot s'écrit-il ?"
            },
            {
                "element_from" : "french",
                "element_to" : "reading",
                "question.text.attribute" : "translations",
                "question.text.attribute.listitem" : 0,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "reading",
                "answer.text.attribute.listitem" : None,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Comment ce mot se lit-il ?"
            }
        ],
        "api" : {
            "name" : "Vocabulaire",
            "subject" : "words",
            "modes" : [
                {
                    "name" : "Du français au japonais",
                    "element_from" : "french",
                    "element_to" : ["char"]
                },
                {
                    "name" : "Du français au japonais et lecture",
                    "element_from" : "french",
                    "element_to" : ["char", "reading"]
                },
                {
                    "name" : "Du japonais au français",
                    "element_from" : "char",
                    "element_to" : ["french"]
                }
            ],
            "focus" : [
                {
                    "name" : "Mots liés au thème de la semaine",
                    "focus" : "theme"
                },
                {
                    "name" : "Mots sur lesquels vous rencontrez des difficultés",
                    "focus" : "weakness"
                },
                {
                    "name" : "Mots aléatoires",
                    "focus" : "random"
                }
            ]
        }
    },
    "kanjis" : {
        "program_names" : {
            "weakness" : "Travailler les kanjis difficiles",
            "random" : "Travailler des kanjis au hasard"
        },
        "item_relations" : [],
        "item_filters" : {},
        "modes" : [
            {
                "element_from" : "char",
                "element_to" : "french",
                "question.text.attribute" : "char",
                "question.text.attribute.listitem" : None,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "translations",
                "answer.text.attribute.listitem" : 0,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Que veut dire ce kanji ?"
            },
            {
                "element_from" : "char",
                "element_to" : "reading",
                "question.text.attribute" : "char",
                "question.text.attribute.listitem" : None,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "readings",
                "answer.text.attribute.listitem" : 0,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Comment se lit ce kanji ?"
            },
            {
                "element_from" : "french",
                "element_to" : "char",
                "question.text.attribute" : "translations",
                "question.text.attribute.listitem" : 0,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "char",
                "answer.text.attribute.listitem" : None,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Quel est le kanji qui correspond à ce concept ?"
            }
        ],
        "api" : {
            "name" : "Kanjis",
            "subject" : "kanjis",
            "modes" : [
                {
                    "name" : "Du français au kanji",
                    "element_from" : "french",
                    "element_to" : ["char"]
                },
                {
                    "name" : "Du kanji au français",
                    "element_from" : "char",
                    "element_to" : ["french"]
                },
                {
                    "name" : "Lecture puis traduction",
                    "element_from" : "char",
                    "element_to" : ["reading", "french"]
                }
            ],
            "focus" : [
                {
                    "name" : "Kanjis sur lesquels vous rencontrez des difficultés",
                    "focus" : "weakness"
                },
                {
                    "name" : "Kanjis aléatoires",
                    "focus" : "random"
                }
            ]
        }
    },
    "hiraganas" : {
        "program_names" : {
            "weakness" : "Travailler les hiraganas difficiles",
            "random" : "Travailler des hiraganas au hasard"
        },
        "item_relations" : [],
        "item_filters" : {},
        "modes" : [
            {
                "element_from" : "reading",
                "element_to" : "char",
                "question.text.attribute" : "pronunciation",
                "question.text.attribute.listitem" : None,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "hiragana",
                "answer.text.attribute.listitem" : None,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Quel est l'hiragana qui correspond à ce son ?"
            },
            {
                "element_from" : "char",
                "element_to" : "reading",
                "question.text.attribute" : "hiragana",
                "question.text.attribute.listitem" : None,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "pronunciation",
                "answer.text.attribute.listitem" : None,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Quel est le son correspondant à cet hiragana ?"
            }
        ],
        "api" : {
            "name" : "Hiraganas",
            "subject" : "hiraganas",
            "modes" : [
                {
                    "name" : "Du son aux hiraganas",
                    "element_from" : "reading",
                    "element_to" : ["char"]
                },
                {
                    "name" : "Des hiraganas au son",
                    "element_from" : "char",
                    "element_to" : ["reading"]
                }
            ],
            "focus" : [
                {
                    "name" : "Hiraganas sur lesquels vous rencontrez des difficultés",
                    "focus" : "weakness"
                },
                {
                    "name" : "Hiraganas aléatoires",
                    "focus" : "random"
                }
            ]
        }
    },
    "katakanas" : {
        "program_names" : {
            "weakness" : "Travailler les katakanas difficiles",
            "random" : "Travailler des katakanas au hasard"
        },
        "item_relations" : [],
        "item_filters" : {},
        "modes" : [
            {
                "element_from" : "reading",
                "element_to" : "char",
                "question.text.attribute" : "pronunciation",
                "question.text.attribute.listitem" : None,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "katakana",
                "answer.text.attribute.listitem" : None,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Quel est le katakana correspondant à ce son ?"
            },
            {
                "element_from" : "char",
                "element_to" : "reading",
                "question.text.attribute" : "katakana",
                "question.text.attribute.listitem" : None,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "pronunciation",
                "answer.text.attribute.listitem" : None,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Quel est le son correspondant à cet hiragana ?"
            }
        ],
        "api" : {
            "name" : "Katakanas",
            "subject" : "katakanas",
            "modes" : [
                {
                    "name" : "Du son aux katakanas",
                    "element_from" : "reading",
                    "element_to" : ["char"]
                },
                {
                    "name" : "Des katakanas au son",
                    "element_from" : "char",
                    "element_to" : ["reading"]
                }
            ],
            "focus" : [
                {
                    "name" : "Katakanas sur lesquels vous rencontrez des difficultés",
                    "focus" : "weakness"
                },
                {
                    "name" : "Katakanas aléatoires",
                    "focus" : "random"
                }
            ]
        }
    },
    "sentences" : {
        "program_names" : {
            "theme" : "Travailler les phrases du thème",
            "weakness" : "Travailler les phrases difficiles",
            "random" : "Travailler des phrases au hasard"
        },
        "item_relations" : [],
        "item_filters" : {},
        "modes" : [
            {
                "element_from" : "french",
                "element_to" : "char",
                "question.text.attribute" : "translation",
                "question.text.attribute.listitem" : None,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "text",
                "answer.text.attribute.listitem" : None,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Comment écrire cette phrase en japonais ?"
            },
            {
                "element_from" : "char",
                "element_to" : "french",
                "question.text.attribute" : "text",
                "question.text.attribute.listitem" : None,
                "question.reading.attribute" : None,
                "question.reading.attribute.listitem" : None,
                "answer.text.attribute" : "translation",
                "answer.text.attribute.listitem" : None,
                "answer.reading.attribute" : None,
                "answer.reading.attribute.listitem" : None,
                "question.instructions" : "Que veut dire cette phrase ?"
            }
        ],
        "api" : {
            "name" : "Phrases",
            "subject" : "sentences",
            "modes" : [
                {
                    "name" : "Du français au japonais",
                    "element_from" : "french",
                    "element_to" : ["char"]
                },
                {
                    "name" : "Du japonais au français",
                    "element_from" : "char",
                    "element_to" : ["french"]
                }
            ],
            "focus" : [
                {
                    "name" : "Phrases liées au thème de la semaine",
                    "focus" : "theme"
                },
                {
                    "name" : "Phrases sur lesquelles vous rencontrez des difficultés",
                    "focus" : "weakness"
                },
                {
                    "name" : "Phrases aléatoires",
                    "focus" : "random"
                }
            ]
        }
    },
    "mix" : {
        "api" : {
            "name" : "Aléatoire",
            "subject" : "mix",
            "modes" : [
                {
                    "name" : "Du français au japonais",
                    "element_from" : "french",
                    "element_to" : ["char_or_reading"]
                },
                {
                    "name" : "Du japonais au français",
                    "element_from" : "char_or_reading",
                    "element_to" : ["french"]
                }
            ],
            "focus" : [
                {
                    "name" : "Sujets aléatoires",
                    "focus" : "random"
                }
            ]
        }
    }
}
