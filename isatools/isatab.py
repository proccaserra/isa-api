from .model.v1 import *
from isatools.io import isatab_parser
import os
import sys
import io
import pandas as pd
import numpy as np


def validate(isatab_dir, config_dir):
    """ Validate an ISA-Tab archive using the Java validator
    :param isatab_dir: Path to ISA-Tab files
    :param config_dir: Path to configuration XML files
    """
    if not os.path.exists(isatab_dir):
        raise IOError("isatab_dir " + isatab_dir + " does not exist")
    print("Using source ISA Tab folder: " + isatab_dir)
    print("ISA configuration XML folder: " + config_dir)
    convert_command = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "convert/isa_line_commands/bin/validate.sh -c " + config_dir + " " + isatab_dir)
    from subprocess import call
    try:
        return_code = call([convert_command], shell=True)
        if return_code < 0:
            print(sys.stderr, "Terminated by signal", -return_code)
        else:
            print(sys.stderr, "Returned", return_code)
    except OSError as e:
        print(sys.stderr, "Execution failed:", e)


def load(isatab_dir):

    def _createOntologySourceReferences(ontology_refs):
        ontologies = []
        for ontology_ref in ontology_refs:
            ontology = OntologySourceReference(
                description=ontology_ref['Term Source Description'],
                file=ontology_ref['Term Source File'],
                name=ontology_ref['Term Source Name'],
                version=ontology_ref['Term Source Version'],
            )
            ontologies.append(ontology)
        return ontologies

    def _createPublications(isapubs, inv_or_study):
        publications = []
        for pub in isapubs:
            publication = Publication(
                pubmed_id=pub[inv_or_study+' PubMed ID'],
                doi=pub[inv_or_study+' Publication DOI'],
                author_list=pub[inv_or_study+' Publication Author List'],
                title=pub[inv_or_study+' Publication Title'],
                status=_createOntologyAnnotationForInvOrStudy(pub, inv_or_study, ' Publication Status')
            )
            publications.append(publication)
        return publications

    def _createOntologyAnnotationForInvOrStudy(object_, inv_or_study, type_):
        onto_ann = OntologyAnnotation(
                name=object_[inv_or_study+type_],
                term_source=object_[inv_or_study+type_+" Term Source REF"],
                term_accession=object_[inv_or_study+type_+" Term Accession Number"],
        )
        return onto_ann

    def _createContacts(contacts, inv_or_study):
        people_json = []
        for contact in contacts:
            person_json = Person(
                last_name=contact[inv_or_study+" Person Last Name"],
                first_name=contact[inv_or_study+" Person First Name"],
                mid_initials=contact[inv_or_study+" Person Mid Initials"],
                email=contact[inv_or_study+" Person Email"],
                phone=contact[inv_or_study+" Person Phone"],
                fax=contact[inv_or_study+" Person Fax"],
                address=contact[inv_or_study+" Person Address"],
                affiliation=contact[inv_or_study+" Person Affiliation"],
                # FIXME Parsing roles?
                roles=[]
            )
            people_json.append(person_json)
        return people_json


    def _createCharacteristicList(node_name, node):
        obj_list = []
        for header in node.metadata:
            if header.startswith("Characteristics"):
                characteristic = header.replace("]", "").split("[")[-1]
                characteristic_obj = Characteristic(
                    value=OntologyAnnotation(name=characteristic)
                )
                obj_item = dict([
                    ("characteristic", characteristic_obj)
                ])
                obj_list.append(obj_item)
        return obj_list

    def _createOntologyAnnotationListForInvOrStudy(array, inv_or_study, type_):
        onto_annotations = []
        for object_ in array:
            onto_ann = OntologyAnnotation(
                name=object_[inv_or_study+type_],
                term_source=object_[inv_or_study+type_+" Term Source REF"],
                term_accession=object_[inv_or_study+type_+" Term Accession Number"],
            )
            onto_annotations.append(onto_ann)
        return onto_annotations

    def _createProtocols(protocols):
        protocols_list = []
        for prot in protocols:
            protocol = Protocol(
                name=prot['Study Protocol Name'],
                protocol_type=_createOntologyAnnotationForInvOrStudy(prot, "Study", " Protocol Type"),
                description=prot['Study Protocol Description'],
                uri=prot['Study Protocol URI'],
                version=prot['Study Protocol Version'],
                parameters=_createProtocolParameterList(prot),
            )
            protocols_list.append(protocol)
        return protocols_list

    def _createProtocolParameterList(protocol):
        parameters_list = []
        parameters_annotations = _createOntologyAnnotationsFromStringList(protocol, "Study",
                                                                          " Protocol Parameters Name")
        for parameter_annotation in parameters_annotations:
            parameter = ProtocolParameter(
                parameterName=parameter_annotation
            )
            # TODO Units?
            parameters_list.append(parameter)
        return parameters_list

    def _createOntologyAnnotationsFromStringList(object_, inv_or_study, type_):
        #FIXME If empty string, it returns 1?
        name_array = object_[inv_or_study+type_].split(";")
        term_source_array = object_[inv_or_study+type_+" Term Source REF"].split(";")
        term_accession_array = object_[inv_or_study+type_+" Term Accession Number"].split(";")
        onto_annotations = []
        for i in range(0, len(name_array)):
             onto_ann = OntologyAnnotation(
                 name=name_array[i],
                 term_source=term_source_array[i],
                 term_accession=term_accession_array[i],
             )
             onto_annotations.append(onto_ann)
        return onto_annotations

    #TODO Finish how to process nodes etc.
    def _createDataFiles(nodes):
        json_dict = dict([])
        for node_index in nodes:
            if nodes[node_index].ntype.endswith("Data File"):
                json_item = Data(
                    name=nodes[node_index].name,
                    type_=nodes[node_index].ntype
                )
                json_dict.update({node_index: json_item})
        return json_dict

    def _createProcessSequence(process_nodes, source_dict, sample_dict, data_dict):
        json_list = []
        for process_node_name in process_nodes:
            try:
                measurement_type = process_nodes[process_node_name].study_assay.metadata["Study Assay Measurement Type"]
            except:
                measurement_type = ""

            try:
                platform = process_nodes[process_node_name].study_assay.metadata["Study Assay Technology Platform"]
            except:
                platform = ""

            try:
                technology = process_nodes[process_node_name].study_assay.metadata["Study Assay Technology Type"]
            except:
                technology = ""

            json_item = dict([
                    ("executesProtocol", _createExecuteStudyProtocol(process_node_name, process_nodes[process_node_name])),
                    ("parameters", []),
                    ("inputs", _createInputList(process_nodes[process_node_name].inputs, source_dict, sample_dict)),
                    ("outputs", _createOutputList(process_nodes[process_node_name].outputs, sample_dict) )
            ])
            json_list.append(json_item)
        return json_list

    def _createExecuteStudyProtocol(process_node_name, process_node):
        json_item = dict([
                   # ("name", dict([("value", process_node_name)])),
                   # ("description", dict([("value", process_node_name)])),
                   # ("version", dict([("value", process_node_name)])),
                   # ("uri", dict([("value", process_node_name)])),
                   # ("parameters", self.createProcessParameterList(process_node_name, process_node))
                ])
        return json_item

    def _createInputList(inputs, source_dict, sample_dict):
        json_list = []
        for argument in inputs:
            try:
                json_item = source_dict[argument]
                json_list.append(json_item)
            except KeyError:
                pass
            try:
                json_item = sample_dict[argument]
                json_list.append(json_item)
            except KeyError:
                pass
        return json_list

    def _createOutputList(arguments, sample_dict):
        json_list = []
        for argument in arguments:
            try:
                json_item = sample_dict[argument]
                json_list.append(json_item)
            except KeyError:
                pass
        return json_list

    # def _createStudyAssaysList(assays):
    #     json_list = []
    #     for assay in assays:
    #         source_dict = _createSourcesDictionary(assay.nodes)
    #         sample_dict = _createSampleDictionary(assay.nodes)
    #         data_dict = _createDataFiles(assay.nodes)
    #         json_item = Assay(
    #             file_name=assay.metadata['Study Assay File Name'],
    #             measurement_type=OntologyAnnotation(
    #                 name=assay.metadata['Study Assay Measurement Type'],
    #                 term_source=assay.metadata['Study Assay Measurement Type Term Source REF'],
    #                 term_accession=assay.metadata['Study Assay Measurement Type Term Accession Number']),
    #             technology_type=OntologyAnnotation(
    #                 name=assay.metadata['Study Assay Technology Type'],
    #                 term_source=assay.metadata['Study Assay Technology Type Term Source REF'],
    #                 term_accession=assay.metadata['Study Assay Technology Type Term Accession Number']),
    #             technology_platform=assay.metadata['Study Assay Technology Platform'],
    #             process_sequence=_createProcessSequence(assay.process_nodes, source_dict, sample_dict, data_dict),
    #         )
    #         json_list.append(json_item)
    #     return json_list

    def _createFactorValueList(self, node_name, node):
        json_list = []
        for header in node.metadata:
            if header.startswith("Factor Value"):
                 factor_value = header.replace("]", "").split("[")[-1]
                 factor_value_ontology_annotation = self.createOntologyAnnotation(factor_value, "", "")
                 factor_value_json = dict([
                     ("value", factor_value_ontology_annotation)
                 ])
                 json_list.append(factor_value_json)
        return json_list

    def _createSourcesSamples(nodes):
        samples_json_dict = dict([])
        sources_obj_dict = dict([])
        for node_index in nodes:
            if nodes[node_index].ntype == "Sample Name":
                sample = Sample(
                    name=node_index,
                    factors=_createFactorValueList(node_index, nodes[node_index]),
                    characteristics=_createCharacteristicList(node_index, nodes[node_index])
                )
                samples_json_dict.update({node_index: sample})
            elif nodes[node_index].ntype == "Source Name":
                source = Source(
                    name=node_index,
                    characteristics=_createCharacteristicList(node_index, nodes[node_index])
                )
                sources_obj_dict.update({node_index: source})
        return sources_obj_dict, samples_json_dict

    def _createStudies(studies):
        study_array = []
        for study in studies:
            sources, samples = _createSourcesSamples(study.nodes)
            data_dict = _createDataFiles(study.nodes)
            study_obj = Study(
                identifier=study.metadata['Study Identifier'],
                title=study.metadata['Study Title'],
                description=study.metadata['Study Description'],
                submission_date=study.metadata['Study Submission Date'],
                public_release_date=study.metadata['Study Public Release Date'],
                factors=None,
                file_name=study.metadata['Study File Name'],
                design_descriptors=_createOntologyAnnotationListForInvOrStudy(study.design_descriptors, "Study",
                                                                              " Design Type"),
                publications=_createPublications(study.publications, "Study"),
                contacts=_createContacts(study.contacts, "Study"),
                protocols=_createProtocols(study.protocols),
                sources=list(sources.values()),
                samples=list(samples.values()),
                process_sequence=_createProcessSequence(study.process_nodes, sources, samples, data_dict),
                assays=_createStudyAssaysList(study.assays),
            )
            study_array.append(study_obj)
        return study_array

    investigation = None
    isa_tab = isatab_parser.parse(isatab_dir)
    if isa_tab is None:
        raise IOError("There was problem parsing the ISA Tab")
    else:
        if isa_tab.metadata != {}:
            #print("isa_tab.metadata->",isa_tab.metadata)
            investigation = Investigation(
                identifier=isa_tab.metadata['Investigation Identifier'],
                title=isa_tab.metadata['Investigation Title'],
                description=isa_tab.metadata['Investigation Description'],
                submission_date=isa_tab.metadata['Investigation Submission Date'],
                public_release_date=isa_tab.metadata['Investigation Public Release Date'],
                ontology_source_references=_createOntologySourceReferences(isa_tab.ontology_refs),
                publications=_createPublications(isa_tab.publications, "Investigation"),
                contacts=_createContacts(isa_tab.contacts, "Investigation"),
                studies=_createStudies(isa_tab.studies),
            )
    return investigation


def dump(isa_obj, path):
    fp = None
    if os.path.exists(path):
        fp = open(os.path.join(path, 'i_investigation.txt'), 'w')
    if isinstance(isa_obj, Investigation):
        # Process Investigation object
        investigation = isa_obj

        # Write ONTOLOGY SOURCE REFERENCE section
        ontology_source_references_df = pd.DataFrame(columns=('Term Source Name',
                                                              'Term Source File',
                                                              'Term Source Version',
                                                              'Term Source Description'
                                                              )
                                                     )
        i = 0
        for ontology_source_reference in investigation.ontology_source_references:
            ontology_source_references_df.loc[i] = [
                ontology_source_reference.name,
                ontology_source_reference.file,
                ontology_source_reference.version,
                ontology_source_reference.description
            ]
            i += 1
        ontology_source_references_df = ontology_source_references_df.set_index('Term Source Name').T
        fp.write('ONTOLOGY SOURCE REFERENCE\n')
        ontology_source_references_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                             index_label='Term Source Name')  # Need to set index_label as top left cell

        # Write INVESTIGATION section
        investigation_df = pd.DataFrame(columns=('Investigation Identifier',
                                                 'Investigation Title',
                                                 'Investigation Description',
                                                 'Investigation Submission Date',
                                                 'Investigation Public Release Date'
                                                 )
                                        )
        investigation_df.loc[0] = [
            investigation.identifier,
            investigation.title,
            investigation.description,
            investigation.submission_date,
            investigation.public_release_date
        ]
        investigation_df = investigation_df.set_index('Investigation Identifier').T
        fp.write('INVESTIGATION\n')
        investigation_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                index_label='Investigation Identifier')  # Need to set index_label as top left cell

        # Write INVESTIGATION PUBLICATIONS section
        investigation_publications_df = pd.DataFrame(columns=('Investigation PubMed ID',
                                                              'Investigation Publication DOI',
                                                              'Investigation Publication Author List',
                                                              'Investigation Publication Status',
                                                              'Investigation Publication Status Term Accession '
                                                              'Number',
                                                              'Investigation Publication Status Term Source REF'
                                                              )
                                                     )
        i = 0
        for investigation_publication in investigation.publications:
            investigation_publications_df.loc[i] = [
                investigation_publication.pubmed_id,
                investigation_publication.doi,
                investigation_publication.author_list,
                investigation_publication.status.name,
                investigation_publication.status.term_source,
                investigation_publication.status.term_accession,
            ]
            i += 1
        investigation_publications_df = investigation_publications_df.set_index('Investigation PubMed ID').T
        fp.write('INVESTIGATION PUBLICATIONS\n')
        investigation_publications_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                             index_label='Investigation PubMed ID')

        # Write INVESTIGATION CONTACTS section
        investigation_contacts_df = pd.DataFrame(columns=('Investigation Person Last Name',
                                                          'Investigation Person First Name',
                                                          'Investigation Person Mid Initials',
                                                          'Investigation Person Email',
                                                          'Investigation Person Phone',
                                                          'Investigation Person Fax',
                                                          'Investigation Person Address',
                                                          'Investigation Person Affiliation',
                                                          'Investigation Person Roles',
                                                          'Investigation Person Roles Term Accession Number',
                                                          'Investigation Person Roles Term Source REF'
                                                          )
                                                 )
        i = 0
        for investigation_contact in investigation.contacts:
            roles = ''
            roles_accession_numbers = ''
            roles_source_refs = ''
            for role in investigation_contact.roles:
                roles += role.name + ';'
                roles_accession_numbers += role.term_accession + ';'
                roles_source_refs += role.term_source.name + ';'
            investigation_contacts_df.loc[i] = [
                investigation_contact.last_name,
                investigation_contact.first_name,
                investigation_contact.mid_initials,
                investigation_contact.email,
                investigation_contact.phone,
                investigation_contact.fax,
                investigation_contact.address,
                investigation_contact.affiliation,
                roles,
                roles_accession_numbers,
                roles_source_refs
            ]
            i += 1
        investigation_contacts_df = investigation_contacts_df.set_index('Investigation Person Last Name').T
        fp.write('INVESTIGATION CONTACTS\n')
        investigation_contacts_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                         index_label='Investigation PubMed ID')

        # Write STUDY sections
        i = 0
        for study in investigation.studies:
            study_df = pd.DataFrame(columns=('Study Identifier',
                                             'Study Title',
                                             'Study Description',
                                             'Study Submission Date',
                                             'Study Public Release Date',
                                             'Study File Name'
                                             )
                                    )
            study_df.loc[i] = [
                study.identifier,
                study.title,
                study.description,
                study.submission_date,
                study.public_release_date,
                study.file_name
            ]
            study_df = study_df.set_index('Study Identifier').T
            fp.write('STUDY\n')
            study_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8', index_label='Study Identifier')

            # Write STUDY DESIGN DESCRIPTORS section
            study_design_descriptors_df = pd.DataFrame(columns=('Study Design Type',
                                                                'Study Design Type Term Accession Number',
                                                                'Study Design Type Term Source REF'
                                                                )
                                                       )
            j = 0
            for design_descriptor in study.design_descriptors:
                study_design_descriptors_df.loc[j] = [
                    design_descriptor.name,
                    design_descriptor.term_accession,
                    design_descriptor.term_source
                ]
                study_design_descriptors_df = study_design_descriptors_df.set_index('Study Design Type').T
                fp.write('STUDY DESIGN DESCRIPTORS\n')
                study_design_descriptors_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                                   index_label='Study Design Type')

            # Write STUDY PUBLICATIONS section
            study_publications_df = pd.DataFrame(columns=('Study PubMed ID',
                                                          'Study Publication DOI',
                                                          'Study Publication Author List',
                                                          'Study Publication Status',
                                                          'Study Publication Status Term Accession Number',
                                                          'Study Publication Status Term Source REF'
                                                          )
                                                 )
            j = 0
            for study_publication in study.publications:
                study_publications_df.loc[j] = [
                    study_publication.pubmed_id,
                    study_publication.doi,
                    study_publication.author_list,
                    study_publication.status.name,
                    study_publication.status.term_source,
                    study_publication.status.term_accession,
                ]
                j += 1
            study_publications_df = study_publications_df.set_index('Study PubMed ID').T
            fp.write('STUDY PUBLICATIONS\n')
            study_publications_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                                 index_label='Study PubMed ID')

            # Write STUDY FACTORS section
            study_factors_df = pd.DataFrame(columns=('Study Factor Name',
                                                     'Study Factor Type',
                                                     'Study Factor Type Term Accession Number',
                                                     'Study Factor Type Term Source REF'
                                                     )
                                            )
            j = 0
            for factor in study.factors:
                study_factors_df.loc[j] = [
                    factor.name,
                    factor.factor_type.name,
                    factor.factor_type.term_accession,
                    factor.factor_type.term_source
                ]
                j += 1
            study_factors_df = study_factors_df.set_index('Study Factor Name').T
            fp.write('STUDY FACTORS\n')
            study_factors_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                    index_label='Study Factor Name')

            # Write STUDY ASSAYS section
            study_assays_df = pd.DataFrame(columns=('Study Assay Measurement Type',
                                                    'Study Assay Measurement Type Term Accession Number',
                                                    'Study Assay Measurement Type Term Source REF',
                                                    'Study Assay Technology Type',
                                                    'Study Assay Technology Type Term Accession Number',
                                                    'Study Assay Technology Type Term Source REF',
                                                    'Study Assay Technology Platform',
                                                    'Study Assay File Name'
                                                    )
                                           )
            j = 0
            for assay in study.assays:
                study_assays_df.loc[j] = [
                    assay.measurement_type.name,
                    assay.measurement_type.term_accession,
                    assay.measurement_type.term_source,
                    assay.technology_type.name,
                    assay.technology_type.term_accession,
                    assay.technology_type.term_source,
                    assay.technology_platform,
                    assay.file_name
                ]
                j += 1
            study_assays_df = study_assays_df.set_index('Study Assay Measurement Type').T
            fp.write('STUDY ASSAYS\n')
            study_assays_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                   index_label='Study Assay Measurement Type')

            # Write STUDY PROTOCOLS section
            study_protocols_df = pd.DataFrame(columns=('Study Protocol Name',
                                                       'Study Protocol Type',
                                                       'Study Protocol Type  Accession Number',
                                                       'Study Protocol Type Source REF',
                                                       'Study Protocol Description',
                                                       'Study Protocol URI',
                                                       'Study Protocol Version',
                                                       'Study Protocol Parameters Name',
                                                       'Study Protocol Parameters Name Term Accession Number',
                                                       'Study Protocol Parameters Name Term Source REF',
                                                       'Study Protocol Components Name',
                                                       'Study Protocol Components Type',
                                                       'Study Protocol Components Type Term Accession Number',
                                                       'Study Protocol Components Type Term Source REF',
                                                       )
                                              )
            j = 0
            for protocol in study.protocols:
                parameters_names = ''
                parameters_accession_numbers = ''
                parameters_source_refs = ''
                for parameter in protocol.parameters:
                    parameters_names += parameter.parameterName.name + ';'
                    parameters_accession_numbers += parameter.parameterName.term_accession + ';'
                    parameters_source_refs += parameter.parameterName.term_source + ';'
                component_names = ''
                component_types = ''
                component_types_accession_numbers = ''
                component_types_source_refs = ''
                for component in protocol.components:
                    component_names += component.name + ';'
                    component_types += component.componentType + ';'
                    component_types_accession_numbers += component.componentType.term_accession + ';'
                    component_types_source_refs += component.componentType.term_source.name + ';'
                study_protocols_df.loc[j] = [
                    protocol.name,
                    protocol.protocol_type.name,
                    protocol.protocol_type.term_accession,
                    protocol.protocol_type.term_source,
                    protocol.description,
                    protocol.uri,
                    protocol.version,
                    parameters_names,
                    parameters_accession_numbers,
                    parameters_source_refs,
                    component_names,
                    component_types,
                    component_types_accession_numbers,
                    component_types_source_refs
                ]
                j += 1
            study_protocols_df = study_protocols_df.set_index('Study Protocol Name').T
            fp.write('STUDY PROTOCOLS\n')
            study_protocols_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                      index_label='Study Protocol Name')

            # Write STUDY CONTACTS section
            study_contacts_df = pd.DataFrame(columns=('Study Person Last Name',
                                                      'Study Person First Name',
                                                      'Study Person Mid Initials',
                                                      'Study Person Email',
                                                      'Study Person Phone',
                                                      'Study Person Fax',
                                                      'Study Person Address',
                                                      'Study Person Affiliation',
                                                      'Study Person Roles',
                                                      'Study Person Roles Term Accession Number',
                                                      'Study Person Roles Term Source REF'
                                                      )
                                             )
            j = 0
            for study_contact in study.contacts:
                # roles = ''
                # roles_accession_numbers = ''
                # roles_source_refs = ''
                # for role in study_contact.roles:
                #     roles += role.name + ';'
                #     roles_accession_numbers += role.term_accession + ';'
                #     roles_source_refs += role.term_source.name + ';'
                study_contacts_df.loc[j] = [
                    study_contact.last_name,
                    study_contact.first_name,
                    study_contact.mid_initials,
                    study_contact.email,
                    study_contact.phone,
                    study_contact.fax,
                    study_contact.address,
                    study_contact.affiliation,
                    '',  # roles,
                    '',  # roles_accession_numbers,
                    '',  # roles_source_refs
                ]
                j += 1
            study_contacts_df = study_contacts_df.set_index('Study Person Last Name').T
            fp.write('STUDY CONTACTS\n')
            study_contacts_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                                     index_label='Study Person Last Name')
        fp.close()

    else:
        raise NotImplementedError("Dumping this ISA object to ISA Tab is not yet supported")
    return fp


def read_investigation_file(fp):

    def _peek(f):
        position = f.tell()
        l = f.readline()
        f.seek(position)
        return l

    def _read_tab_section(f, sec_key, next_sec_key=None):

        line = f.readline()
        if not line.rstrip() == sec_key:
            raise IOError("Expected: " + sec_key + " section, but got: " + line)
        memf = io.StringIO()
        while not _peek(f=f).rstrip() == next_sec_key:
            line = f.readline()
            if not line:
                break
            memf.write(line)
        memf.seek(0)
        return memf

    def _build_section_df(f):
        df = pd.read_csv(f, sep='\t').T  # Load and transpose ISA file section
        df.replace(np.nan, '', regex=True, inplace=True)  # Strip out the nan entries
        df.reset_index(inplace=True)  # Reset index so it is accessible as column
        df.columns = df.iloc[0]  # If all was OK, promote this row to the column headers
        df = df.reindex(df.index.drop(0))  # Reindex the DataFrame
        return df

    # Read in investigation file into DataFrames first
    ontology_sources_df = _build_section_df(_read_tab_section(
        f=fp,
        sec_key='ONTOLOGY SOURCE REFERENCE',
        next_sec_key='INVESTIGATION'
    ))
    # assert({'Term Source Name', 'Term Source File', 'Term Source Version', 'Term Source Description'}
    #        .issubset(set(ontology_sources_df.columns.values)))  # Check required labels are present
    investigation_df = _build_section_df(_read_tab_section(
        f=fp,
        sec_key='INVESTIGATION',
        next_sec_key='INVESTIGATION PUBLICATIONS'
    ))
    investigation_publications_df = _build_section_df(_read_tab_section(
        f=fp,
        sec_key='INVESTIGATION PUBLICATIONS',
        next_sec_key='INVESTIGATION CONTACTS'
    ))
    investigation_contacts_df = _build_section_df(_read_tab_section(
        f=fp,
        sec_key='INVESTIGATION CONTACTS',
        next_sec_key='STUDY'
    ))
    study_df_list = list()
    study_design_descriptors_df_list = list()
    study_publications_df_list = list()
    study_factors_df_list = list()
    study_assays_df_list = list()
    study_protocols_df_list = list()
    study_contacts_df_list = list()
    while _peek(fp):  # Iterate hopefully through STUDY blocks until end of file
        study_df_list.append(_build_section_df(_read_tab_section(
            f=fp,
            sec_key='STUDY',
            next_sec_key='STUDY DESIGN DESCRIPTORS'
        )))
        study_design_descriptors_df_list.append(_build_section_df(_read_tab_section(
            f=fp,
            sec_key='STUDY DESIGN DESCRIPTORS',
            next_sec_key='STUDY PUBLICATIONS'
        )))
        study_publications_df_list.append(_build_section_df(_read_tab_section(
            f=fp,
            sec_key='STUDY PUBLICATIONS',
            next_sec_key='STUDY FACTORS'
        )))
        study_factors_df_list.append(_build_section_df(_read_tab_section(
            f=fp,
            sec_key='STUDY FACTORS',
            next_sec_key='STUDY ASSAYS'
        )))
        study_assays_df_list.append(_build_section_df(_read_tab_section(
            f=fp,
            sec_key='STUDY ASSAYS',
            next_sec_key='STUDY PROTOCOLS'
        )))
        study_protocols_df_list.append(_build_section_df(_read_tab_section(
            f=fp,
            sec_key='STUDY PROTOCOLS',
            next_sec_key='STUDY CONTACTS'
        )))
        study_contacts_df_list.append(_build_section_df(_read_tab_section(
            f=fp,
            sec_key='STUDY CONTACTS',
            next_sec_key='STUDY'
        )))

    # # Start building the object model
    # ontology_source_references = list()
    # for x in ontology_sources_df.iterrows():  # Iterate over the rows to build our OntologySourceReference objs
    #     ontology_source_data = x[1]  # Get data out of df row
    #     ontology_source = OntologySourceReference(
    #         name=ontology_source_data['Term Source Name'],
    #         file=ontology_source_data['Term Source File'],
    #         version=ontology_source_data['Term Source Version'],
    #         description=ontology_source_data['Term Source Description']
    #     )
    #     print(ontology_source.to_json())
    #     ontology_source_references.append(ontology_source)
    # investigation_data = investigation_df[1]
    # investigation = Investigation(
    #     identifier=investigation_data['Investigation Identifier'],
    #     title=investigation_data['Investigation Title'],
    #     description=investigation_data['Investigation Description'],
    #     submission_date=investigation_data['Investigation Submission Date'],
    #     public_release_date=investigation_data['Investigation Public Release Date'],
    # )
    # for x in investigation_publications_df.iterrows():
    #     investigation_publication_data = x[1]
    #     investigation_publication = Publication(
    #         pubmed_id=investigation_publication_data['Investigation PubMed ID'],
    #         doi=investigation_publication_data['Investigation Publication DOI'],
    #         author_list=investigation_publication_data['Investigation Publication Author List'],
    #         title=investigation_publication_data['Investigation Publication Title'],
    #         status=OntologyAnnotation(
    #             name=investigation_publication_data['Investigation Publication Status'],
    #             term_accession=investigation_publication_data['Investigation Publication Status Term Accession'],
    #             term_source=investigation_publication_data['Investigation Publication Status Term Source REF'],
    #         )
    #     )
    #     investigation.publications.append(investigation_publication)
    return investigation_df
