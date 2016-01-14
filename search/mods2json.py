"""Module takes Colorado College's MODS XML metadata and extracts information
into a Python dictionary that is converted into JSON and used as an
Elasticsearch document body.

"""
__author__ = "Jeremy Nelson"

import rdflib
MODS = rdflib.Namespace("http://www.loc.gov/mods/v3")


def generate_field_name(text):
    """Helper function takes text, removes spaces, lowercase for first term,
    and title case for remaining terms before returning a field name for
    indexing into Elasticsearch

    Args:
        text: Text to generate field name
    Returns:
        str: String for field name
    """
    if text is None:
        return
    terms = [s.title() for s in text.split()]
    terms[0] = terms[0].lower()
    return ''.join(terms)


def access_condition2rdf(mods):
    """Function takes MODS XML document and processes mods:accessCondition

    Args:
        mods: MODS etree Document

    Returns:
        dict: Dictionary of extracted Rights statement
    """
    output = {}
    accessCondition = mods.find("{{{0}}}accessCondition".format(MODS))
    if accessCondition is not None:
        if accessCondition.attrib.get("type", "").startswith("useAnd"):
            output["useAndReproduction"] = accessCondition.text
    return output


def language2rdf(mods):
    """Function takes MODS XML document and processes mods:language

    Args:
        mods: MODS etree Document

    Returns:
        dict: Dictionary of extracted language metadata
    """
    output = {'language': []}
    xpath = "{{{0}}}language/{{{0}}}languageTerm".format(MODS)
    languageTerms = mods.findall(xpath)
    for row in languageTerms:
        output['language'].append(row.text)
    if len(output['language']) < 1:
        output.pop('language')
    return output

def names2rdf(mods):
    """Function takes MODS XML document and processes mods:names

    Args:
        mods: MODS etree Document

    Returns:
        dict: Dictionary of extracted names
    """
    names = mods.findall("{{{0}}}name".format(MODS))
    output = {}
    for row in names:
        name = row.find("{{{0}}}namePart".format(MODS))
        if hasattr(name, "text") and name.text is None:
            continue
        roleTerm = row.find("{{{0}}}role/{{{0}}}roleTerm".format(MODS))
        if roleTerm is not None and hasattr(roleTerm, "text"):
            if roleTerm.text is None:
                continue
            field = generate_field_name(roleTerm.text)
            if hasattr(output, field):
                if not name.text in output[field]:
                    output[field].append(name.text)
            else:
                output[field] = [name.text,]
    return output

def notes2rdf(mods):
    """Function takes MODS XML document and processes mods:notes

	Args:
        mods: MODS etree Document

    Returns:
        dict: Dictionary of extracted notes
    """
    def process_note(field_name, text):
        """Helper function takes a field name and text checks to see if the
        note is unique in the output dict or adds as the field with the text
        as first member in a list.

        Args:
            field_name: Name of the field to check in output
            text: Text from the note.
        """
        if field_name in output.keys():
            if not text in output[field_name]:
                output[field_name].append(text)
        else:
            output[field_name] = [text,]
    output = {}
    notes = mods.findall("{{{0}}}note".format(MODS))
    for note in notes:
        if not hasattr(note, "text"):
            continue
        note_type = note.attrib.get('type', '')
        if note_type.startswith("admin"):
            process_note("adminNote", note.text)
        if note_type.startswith("thesis"):
            displayLabel = note.attrib.get('displayLabel', '')
            if displayLabel.startswith("Degree"):
                process_note(
                    generate_field_name(displayLabel),
                    note.text)
            else:
                process_note("thesis", note.text)
        else:
            process_note("note", note.text)
    return output


def originInfo2rdf(mods):
    """Function takes MODS XML document and processes mods:originInfo

    Args:
        mods: MODS etree Document

    Returns:
        dict: Dictionary of extracted notes 
    """
    output = {}
    originInfo = mods.find("{{{0}}}originInfo".format(MODS))
    if not originInfo:
        return output
    place = originInfo.find("{{{0}}}place/{{{0}}}placeTerm".format(MODS))
    if place is not None and place.text is not None:
        output['place'] = place.text
    publisher = originInfo.find("{{{0}}}publisher".format(MODS))
    if publisher is not None and publisher.text is not None:
        output['publisher'] = publisher.text
    copyrightDate = originInfo.find("{{{0}}}copyrightDate".format(MODS))
    if copyrightDate is not None and copyrightDate.text is not None:
        output["copyrightDate"] = copyrightDate.text
    dateCreated = originInfo.find("{{{0}}}dateCreated".format(MODS))
    if dateCreated is not None and dateCreated.text is not None:
        output["dateCreated"] = dateCreated.text
    dateIssued = originInfo.find("{{{0}}}dateIssued".format(MODS))
    if dateIssued is not None and dateIssued.text is not None:
        output["dateIssued"] = dateIssued.text 
    return output
    

def physicalDescription2rdf(mods):
    """Function takes MODS XML document and processes mods:physicalDescription

    Args:
        mods: MODS etree Document

    Returns:
        dict: Dictionary of extracted extent and digitalOrigin from MODS 
              metadata.
    """
    output = {}
    physicalDescription = mods.find("{{{0}}}physicalDescription".format(MODS))
    if not physicalDescription:
        return output
    extent = physicalDescription.find("{{{0}}}extent".format(MODS))
    if extent is not None and extent.text is not None:
        #! Should add maps and illustrations and page numbers as separate
        #! ES aggregations?
        output['extent'] = extent.text
    digitalOrigin = physicalDescription.find(
        "{{{0}}}digitalOrigin".format(MODS))
    if digitalOrigin is not None and digitalOrigin.text is not None:
        output["digitalOrigin"] = digitalOrigin.text
    return output

def singleton2rdf(mods, element_name):
    """Function takes MODS XML document and processes mods:originInfo

    Args:
        mods: MODS etree Document

    Returns:
        dict: Dictionary of extracted notes 
    """
    output = {}
    output[element_name] = []
    pattern = "{{{0}}}{1}".format(MODS, element_name)
    elements = mods.findall(pattern)
    for element in elements:
        if not element.text in output[element_name]:
            output[element_name].append(element.text)
    if len(output[element_name]) > 0:
        return output
    return dict()
    

def subject2rdf(mods):
    """Function takes MODS XML document and processes mods:subject

    Args:
        mods: MODS etree Document

    Returns:
        dict: Dictionary of extracted subjects 
    """
    def process_subject(subject, element_name):
        """Helper function either adds a new subject with the element
	    name, extracts the element from the MODS element and adds a
        unique subject to the output dictionary.
       
        Args:
            subject: MODS subject element
            element_name: element's name
        """
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
        process_subject(row, "topic")
    return output
        

def title2rdf(mods):
    """
    Function takes a MODS document and returns the titles

	Args:
       mods -- MODS etree XML document
    """
    output = {}
    titles = mods.findall("{{{0}}}titleInfo".format(MODS))
    for row in titles:
        title = row.find("{{{0}}}title".format(MODS))
        type_of = row.attrib.get("type", "")
        if title is None:
            continue
        if type_of.startswith("alt"):
            output["titleAlternative"] = title.text
        else:
            output["titlePrincipal"] = title.text
    return output
   
def url2rdf(mods):
    """
    Function takes a MODS document and returns the urls as 
    the handle.

	Args:
       mods -- MODS etree XML document
    """
    url = mods.find("{{{0}}}location/{{{0}}}url".format(MODS))
    #! Saves as handle identifier
    if hasattr(url, "text"):
        return {"handle": url.text}
    return {}

def mods2rdf(mods):
    """Function class all functions to transform a etree MODS doc
    into RDF JSON to be indexed into Elasticsearch.

	Args:
        mods -- MODS etree XML document
    Returns:
        Dictionary of RDF for indexing into Elasticsearch
    """
    rdf_json = {}
    rdf_json.update(singleton2rdf(mods, "abstract"))
    rdf_json.update(access_condition2rdf(mods))
    rdf_json.update(singleton2rdf(mods, "genre"))
    rdf_json.update(language2rdf(mods))
    rdf_json.update(names2rdf(mods))
    rdf_json.update(notes2rdf(mods))
    rdf_json.update(originInfo2rdf(mods))
    rdf_json.update(physicalDescription2rdf(mods))
    rdf_json.update(subject2rdf(mods))
    rdf_json.update(title2rdf(mods))
    rdf_json.update(singleton2rdf(mods, "typeOfResource"))
    rdf_json.update(url2rdf(mods))
    return rdf_json
