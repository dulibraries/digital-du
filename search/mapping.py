"""Elasticsearch Mapping for DACC Repository"""
__author__ = "Jeremy Nelson"

MAP = {"mappings": {
    "mods": {
        "properties": {
            "abstract": {
                "type": "string"
            },
            "adminNote": {
                "type": "string"
            },
            "contributor": {
                "type": "string"
            },
            "creator": {
                "type": "string"
            },
            "dateCreated": {
               "index": "not_analyzed",
                "type": "string"
				
            },
            "dateIssued": {
                "type": "string"
            },
			"datePublished": {
					"index": "not_analyzed",
					"type": "string"
			},
            "degreeGrantor": {
                "type": "string"
            },
            "degreeName": {
                "type": "string"
            },
            "degreeType": {
                "type": "string"
            },
            "digitalOrigin": {
                "type": "string"
            },
            "extent": {
                "type": "string"
            },
            "genre": {
                "type": "string"
            },
            "handle": {
                "type": "string"
            },
            "inCollection": {
                "index": "not_analyzed",
                "type": "string"
            },
            "language": {
                "type": "string"
            },
            "note": {
                "type": "string"
            },
            "photographer": {
                "type": "string"
            },
            "pid": {
                "index": "not_analyzed",
                "type": "string"
            },
            "place": {
                "type": "string"
            },
            "publisher": {
                "type": "string"
            },
            "sponsor": {
                "type": "string"
            },
            "subject": {
                "properties": {
                    "genre": {
						"index": "not_analyzed",
                        "type": "string"
                    },
                    "geographic": {
						"index": "not_analyzed",
                        "type": "string"
                    },
                    "temporal": {
						"index": "not_analyzed",
                        "type": "string"
                    },
                    "topic": {
						"index": "not_analyzed",
                        "type": "string"
                    }
                }
            },
            "thesis": {
                "type": "string"
            },
            "thesisAdvisor": {
                "type": "string"
            },
            "titleAlternative": {
                "type": "string"
            },
            "titlePrincipal": {
                "type": "string"
            },
            "typeOfResource": {
                "index": "not_analyzed",
                "type": "string"
            },
            "useAndReproduction": {
                "type": "string"
            }
            }
        }
    }
}
