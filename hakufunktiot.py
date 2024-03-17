import requests
import time
import json

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
