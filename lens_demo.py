import json
import requests
import pandas as pd
import streamlit as st
import time

def get_patent_data(start_date, end_date, terms, token, class_cpc_prefix=None):
    url = 'https://api.lens.org/patent/search'
    include = ["lens_id", "date_published", "jurisdiction", "biblio", "doc_key", 
               "publication_type", "families", "biblio.publication_reference", 
               "biblio.invention_title.text", "abstract.text", "claims.claims.claim_text"]

    should_clauses = []
    for term in terms:
        should_clauses.extend([
            {
                "match_phrase": {
                    "title": term
                }
            },
            {
                "match_phrase": {
                    "abstract": term
                }
            },
            {
                "match_phrase": {
                    "claim": term
                }
            },
            {
                "match_phrase": {
                    "description": term
                }
            },
            {
                "match_phrase": {
                    "full_text": term
                }
            }
        ])

    if class_cpc_prefix:
        should_clauses.append({
            "prefix": {
                "class_cpc.symbol": class_cpc_prefix
            }
        })

    must_clauses = [
        {
            "bool": {
                "should": should_clauses
            }
        },
        {
            "range": {
                "date_published": {
                    "gte": start_date,
                    "lte": end_date
                }
            }
        }
    ]

    query_body = {
        "query": {
            "bool": {
                "must": must_clauses
            }
        },
        "size": 500,
        "scroll": "1m",
        "include": include
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    request_body = json.dumps(query_body)
    
    patents = []
    scroll_id = None

    while True:
        if scroll_id is not None:
            request_body = json.dumps({"scroll_id": scroll_id, "include": include}, ensure_ascii=False)
        response = requests.post(url, data=request_body.encode('utf-8'), headers=headers)
        if response.status_code == requests.codes.too_many_requests:
            print("TOO MANY REQUESTS, waiting...")
            time.sleep(8)
            continue
        if response.status_code != requests.codes.ok:
            print("ERROR:", response)
            break
        response = response.json()
        patents = patents + response['data']
        print(len(patents), "/", response['total'], "patents read...")
        if response['scroll_id'] is not None:
            scroll_id = response['scroll_id']
        if len(patents) >= response['total'] or len(response['data']) == 0:
            break

    data_out = {"total": len(patents), "data": patents}
    q = json.dumps(data_out)
    json_data = json.loads(q)
    patent_data = json_data["data"]
    return patent_data

def get_publication_data(start_date, end_date, phrases, token):
    url = 'https://api.lens.org/scholarly/search'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    should_clauses = []
    for phrase in phrases:
        should_clauses.extend([
            {"match_phrase": {"title": phrase}},
            {"match_phrase": {"abstract": phrase}},
            {"match_phrase": {"full_text": phrase}},
        ])

    query_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "should": should_clauses
                        }
                    },
                    {
                        "range": {
                            "date_published": {
                                "gte": start_date,
                                "lte": end_date
                            }
                        }
                    }
                ]
            }
        },
        "size": 500,
        "scroll": "1m"
    }

    publications = []
    scroll_id = None

    while True:
        if scroll_id is not None:
            query_body = {"scroll_id": scroll_id}

        response = requests.post(url, json=query_body, headers=headers)

        if response.status_code == requests.codes.too_many_requests:
            print("TOO MANY REQUESTS, waiting...")
            time.sleep(8)
            continue

        if response.status_code != requests.codes.ok:
            print("ERROR:", response)
            break

        response_data = response.json()
        publications += response_data['data']
        
        print(f"{len(publications)} / {response_data['total']} publications read...")

        if response_data['scroll_id'] is not None:
            scroll_id = response_data['scroll_id']
        
        if len(publications) >= response_data['total'] or len(response_data['data']) == 0:
            break

    data_out = {"total": len(publications), "data": publications}
    return data_out

def patents_table(json_records):

    table_data = []

    for record in json_records:
        biblio = record.get('biblio', {})
        publication_reference = biblio.get('publication_reference', {})
        application_reference = biblio.get('application_reference', {})
        priority_claims = biblio.get('priority_claims', {})
        invention_titles = biblio.get('invention_title', [])
        parties = biblio.get('parties', {}) or {}
        abstract = record.get('abstract',[])
        
        owners_all = parties.get('owners_all', [{}])
        extracted_name = None
        if owners_all:
            extracted_name = owners_all[0].get('extracted_name', None)
        
        selected_abstract_lang = None
        # Choose the invention title based on the preferred language order
        selected_title = None
        for lang in ['en', 'fi']:
            for title in invention_titles:
                if title.get('lang') == lang:
                    selected_title = title.get('text')
                    selected_abstract_lang = abstract[0].get('lang') if abstract else None
                    break
            if selected_title:
                break
        if not selected_title:
            selected_title = invention_titles[0].get('text') if invention_titles else None
        
        selected_abstract = None
        for lang in ['en', 'fi']:
            for ab in abstract:
                if ab.get('lang') == lang:
                    selected_ab = ab.get('text')
                    
                    break
            if selected_abstract:
                break
        if not selected_abstract:
            selected_abstract = abstract[0].get('text') if abstract else None
            
        row = {
            'lens_id': record.get('lens_id', None),
            'jurisdiction': record.get('jurisdiction', None),
            'date_published': record.get('date_published', None),
            'doc_key': record.get('doc_key', None),
            'publication_type': record.get('publication_type', None),
            'publication_reference_jurisdiction': publication_reference.get('jurisdiction', None),
            #'publication_reference_doc_number': publication_reference.get('doc_number', None),
            'publication_reference_kind': publication_reference.get('kind', None),
            'publication_reference_date': publication_reference.get('date', None),
            'application_reference_jurisdiction': application_reference.get('jurisdiction', None),
            #'application_reference_doc_number': application_reference.get('doc_number', None),
            'application_reference_kind': application_reference.get('kind', None),
            'application_reference_date': application_reference.get('date', None),
            'priority_claims_earliest_claim_date': priority_claims.get('earliest_claim', {}).get('date', None),
            'invention_title': selected_title,
            'numApplicants': len(parties.get('applicants', [])),
            'numInventors': len(parties.get('inventors', [])),
            'references_cited_patent_count': biblio.get('references_cited', {}).get('patent_count', None),
            'references_cited_npl_count': biblio.get('references_cited', {}).get('npl_count', None),
            'priority_claim_jurisdiction': priority_claims.get('claims', [{}])[0].get('jurisdiction', None),
            'abstract': selected_abstract,
            'abstract_lang': selected_abstract_lang,
            'owner': extracted_name  #
        }
        table_data.append(row)

    df = pd.DataFrame(table_data)
    return df

def cpc_classifications_table(json_records):
    table_data = []
    for record in json_records:
        lens_id = record.get('lens_id', None)
        classifications_cpc = record.get('biblio', {}).get('classifications_cpc', {}).get('classifications', [])

        for classification in classifications_cpc:
            row = {
                'lens_id': lens_id,
                'cpc_classification': classification.get('symbol', None),
                'class': classification['symbol'][0] if classification.get('symbol', None) else None,
                'cpc_code_split': classification['symbol'].split('/')[0] if classification.get('symbol', None) else None,
            }
            table_data.append(row)
    
    df = pd.DataFrame(table_data)
    return df

def applicants_table(json_records):
    
    table_data = []

    for record in json_records:
        biblio = record.get('biblio', {})
        parties = biblio.get('parties', {}) or {}
        applicants = parties.get('applicants', [{}])

        for applicant in applicants:
            row = {
                'lens_id': record.get('lens_id', None),
                'doc_key': record.get('doc_key', None),
                'residence': applicant.get('residence', None),
                'extracted_name': applicant.get('extracted_name', {}).get('value', None),
                'extracted_address': applicant.get('extracted_address', None),
                'nimi': applicant.get('extracted_name', {}).get('value', None),
                'id': applicant.get('sequence', None),
                
            }
            table_data.append(row)

    df = pd.DataFrame(table_data)
    return df

def families_table(json_records):
    table_data = []
    for record in json_records:
        simple_family = record.get('families', {}).get('simple_family', {})
        for member in simple_family.get('members', []):
            document_id = member.get('document_id', {})
            lens_id = member.get('lens_id', None)

            row = {
                'lens_id': record.get('lens_id', None),
                'doc_key': record.get('doc_key', None),
                'family_size': simple_family.get('size', None),
                'family_lens_id': lens_id,
                'family_jurisdiction': document_id.get('jurisdiction', None),
                'doc_number': document_id.get('doc_number', None),
                'family_kind': document_id.get('kind', None),
                'family_date': document_id.get('date', None),
            }
            table_data.append(row)
    df = pd.DataFrame(table_data)
    return df

def breakdown_cpc(code):
    section = code[0]
    c_class = code[:3]
    subclass = code[:4]
    group = code.split('/')[0]
    subgroup = code
    return pd.Series([section, c_class, subclass, group, subgroup])

def make_cpc(df, cpc_json_file):
    
    cpc = pd.read_json(cpc_json_file)
    df[['Section', 'Class', 'Subclass', 'Group', 'Subgroup']] = df['cpc_classification'].apply(breakdown_cpc)
    df['Group'] = df['Group'].apply(lambda x: x + "/00")
    df.drop(['cpc_code_split', 'class'], axis=1, inplace=True)
    df['Section Description'] = df['Section'].map(cpc.set_index('Code')['Description'])
    df['Class Description'] = df['Class'].map(cpc.set_index('Code')['Description'])
    df['Subclass Description'] = df['Subclass'].map(cpc.set_index('Code')['Description'])
    df['Group Description'] = df['Group'].map(cpc.set_index('Code')['Description'])
    df['Subgroup Description'] = df['Subgroup'].map(cpc.set_index('Code')['Description'])

    return df

def fields_of_study_table(publication_data):
    table_data = []

    for record in publication_data['data']:
        lens_id = record.get('lens_id', None)
        fields_of_study = record.get('fields_of_study', [])

        for field in fields_of_study:
            row = {
                'lens_id': lens_id,
                'field_of_study': field
            }
            table_data.append(row)

    df = pd.DataFrame(table_data)
    return df

def publication_table(json_data):
    
    data_list = json_data['data']

    columns = ["lens_id","title", "publication_type", "year_published", 
               "date_published_parts", "created", 
               "source", "references_count", 
               "start_page", "end_page", "author_count", 
               "abstract", "source_urls"]  

    
    data = [{key: item[key] if key in item else None for key in columns} for item in data_list]
    df = pd.DataFrame(data)

    df["source_title"] = df["source"].apply(lambda x: x.get("title") if x else None)
    df["source_publisher"] = df["source"].apply(lambda x: x.get("publisher") if x else None)
    df = df.drop(columns="source")

    df["url"] = df["source_urls"].apply(lambda x: x[0]["url"] if x else None)

    df = df.drop(columns="source_urls")

    return df


st.title('Data search from patents and publications')

data_type = st.multiselect('Select Data Type', ['Patents', 'Publications'], default=['Patents'])

start_date = st.text_input('Start Date (YYYY-MM-DD)', value='2020-01-01')
end_date = st.text_input('End Date (YYYY-MM-DD)', value='2020-01-31')
terms = st.text_area('Search Terms (comma-separated)').split(',')

token = st.secrets["mytoken"]
class_cpc_prefix = st.text_input('CPC Class Prefix (Optional)', '')

if st.button('Fetch Data'):
    try:
        if 'Patents' in data_type:
            patent_data = get_patent_data(start_date, end_date, [term.strip() for term in terms], token, class_cpc_prefix or None)
            if patent_data:
                st.write("Fetched {} patents".format(len(patent_data)))
                p = patents_table(patent_data)
                st.dataframe(pd.DataFrame(p))  
            else:
                st.write("No patent data fetched. Please check your inputs and try again.")
                
        if 'Publications' in data_type:
            publication_data = get_publication_data(start_date, end_date, [term.strip() for term in terms], token)
            if publication_data['data']:
                st.write("Fetched {} publications".format(len(publication_data['data'])))
                pub = publication_table(publication_data)
                st.dataframe(pd.DataFrame(pub))
            else:
                st.write("No publication data fetched. Please check your inputs and try again.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

#c = cpc_classifications_table(patent_data)
#c = make_cpc(c, 'cpc_ultimate_titles.json')
#st.dataframe(c)
