__author__ = "Jeremy Nelson"

import rdflib
MODS = rdflib.Namespace("http://www.loc.gov/mods/v3")


def accessCondition2rdf(mods):
    accessCondition = mods.find("{{{0}}}accessCondition".format(MODS))
    if hasattr(accessCondition, "type") and hasattr(accessCondition, "text"):
        return {"useAndReproduction": accessCondition.text}
    return {}

def names2rdf(mods):
    names = mods.findall("{{{0}}}name".format(MODS))
    output = {'creator': [], 'contributor': []}
    for row in names:
        name = row.find("{{{0}}}namePart".format(MODS))
        if name.text is None:
            continue
        roleTerm = row.find("{{{0}}}role/{{{0}}}roleTerm".format(MODS))
        if roleTerm.text.startswith("creator"):
            if not name.text in output['creator']:
                output['creator'].append(name.text)
    return output

def notes2rdf(mods):
    output = {"note": [], "adminNote": []}
    notes = mods.findall("{{{0}}}note".format(MODS))
    for note in notes:
        if not hasattr(note, "text"):
            continue
        if note.attrib.get('type', '').startswith("admin"):
            output["adminNote"].append(note.text)
        else:
            output["note"].append(note.text)
    if len(output['note']) < 1:
        output.pop('note')
    if len(output['adminNote']) < 1:
        output.pop('adminNote')
    return output
           

def originInfo2rdf(mods):
    output = {}
    originInfo = mods.find("{{{0}}}originInfo".format(MODS))
    place = originInfo.find("{{{0}}}place/{{{0}}}placeTerm".format(MODS))
    if place.text is not None:
        output['place'] = place.text
    publisher = mods.find("{{{0}}}publisher".format(MODS))
    if publisher and publisher.text is not None:
        output['publisher'] = publisher.text
    dateCreated = originInfo.find("{{{0}}}dateCreated".format(MODS))
    if dateCreated and dateCreated.text is not None:
        output["dateCreated"] = dateCreated.text
    copyrightDate = originInfo.find("{{{0}}}copyrightDate".format(MODS))
    if copyrightDate and copyrightDate.text is not None:
        output["copyrightDate"] = copyrightDate.text
    return output
    

def singleton2rdf(mods, element_name):
    output = {}
    output[element_name] = []
    pattern = "{{{0}}}{1}".format(MODS, element_name)
    elements = mods.findall(pattern)
    for element in elements:
        if not element.text in output[element_name]:
            output[element_name].append(element.text)
    return output

def subject2rdf(mods):
    def process_subject(subject, element_name):
        element = subject.find("{{{0}}}{1}".format(MODS, element_name))
        if hasattr(element, "text"):
            if element_name in output["subject"].keys():
                if not element.text in output["subject"][element_name]:
                    output["subject"][element_name].append(element.text)
            else:
                output["subject"][element_name] = [element.text, ]
    output = {"subject":{}}
    subjects = mods.findall("{{{0}}}subject".format(MODS))
    for row in subjects:
        process_subject(row, "genre")
        process_subject(row, "geographic")
        names = row.findall("{{{0}}}name".format(MODS))
        for name in names:
            namePart = name.find("{{{0}}}namePart".format(MODS))
            if namePart and namePart.text is not None:
                if "name" in output['subject'].keys():
                    if not namePart.text in output['subject']['name']:
                        output["subject"]["name"].append(namePart.text)
                else:
                    output["subject"]["name"] = [namePart.text, ]
        process_subject(row, "temporal")
    return output
        

def title2rdf(mods):
    """
    Function takes a MODS document and returns the titles

    args
       mods -- MODS etree XML document
    """
    output = {}
    titles = mods.findall("{{{0}}}titleInfo".format(MODS))
    for row in titles:
        title = row.find("{{{0}}}title".format(MODS))
        type_of = row.attrib.get("type", "")
        if type_of.startswith("alt"):
            output["titleAlternative"] = title.text
        else:
            output["titlePrincipal"] = title.text
    return output
   
def url2rdf(mods):
    url = mods.find("{{{0}}}location/{{{0}}}url".format(MODS))
    #! Saves as handle identifier
    if hasattr(url, "text"):
        return {"handle": url.text}

def mods2rdf(mods):
    rdf_json = {}
    rdf_json.update(singleton2rdf(mods, "abstract"))
    rdf_json.update(accessCondition2rdf(mods))
    rdf_json.update(singleton2rdf(mods, "genre"))
    rdf_json.update(names2rdf(mods))
    rdf_json.update(notes2rdf(mods))
    rdf_json.update(originInfo2rdf(mods))
    rdf_json.update(subject2rdf(mods))
    rdf_json.update(title2rdf(mods))
    rdf_json.update(singleton2rdf(mods, "typeOfResource"))
    rdf_json.update(url2rdf(mods))
    return rdf_json
