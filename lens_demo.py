import streamlit as st
import pandas as pd
from openai import OpenAI
from hakufunktiot import *
from datanmuokkausfunktiot import *

client = OpenAI(api_key=st.secrets["openai_api_key"])

def get_synonyms(term):
    try:
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": f"What are synonyms or related terms for '{term}'?"
                }
            ],
        )
        if chat_completion.choices:
            response_content = chat_completion.choices[0].message.content
            return response_content
    except Exception as e:
        st.error(f"An error occurred while fetching synonyms: {e}")
        return "Error fetching synonyms"
        
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>Datahaku patenteista ja julkaisuista</h1>", unsafe_allow_html=True)

main_row = st.columns([2, 1, 2]) 

with main_row[0]:
    image_url = 'https://raw.githubusercontent.com/XamkDataLab/lens_demo/main/DALL.jpg'
    st.image(image_url)

with main_row[1]:
    data_type = st.multiselect('Valitse tietokanta', ['Patentit', 'Julkaisut'], default=['Patentit', 'Julkaisut'])
    start_date = st.date_input('Alkaen', value=pd.to_datetime('2024-01-01'))
    end_date = st.date_input('Päättyen', value=pd.to_datetime('2024-03-01'))

with main_row[2]:
    class_cpc_prefix = st.text_input('CPC-luokitus (patenteille, voi jättää tyhjäksi)', '')
    terms = st.text_area('Hakutermit (erota pilkulla, operaattori OR)', 
                        value='low carbon concrete', 
                        height=300).split(',')

if st.button("Get Synonyms for Provided Terms"):
    if terms: 
        for term in terms:
            synonyms = get_synonyms(term.strip())
            if synonyms:
                st.write(f"**{term}**: {synonyms}")
            else:
                st.write(f"**{term}**: No synonyms found.")
    else:
        st.write("No terms provided.")

token = st.secrets["mytoken"]


if st.button('Hae Data'):
    try:
        if 'Patentit' in data_type:
            patent_data = get_patent_data(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), [term.strip() for term in terms], token, class_cpc_prefix or None)
            if patent_data:
                st.write(f"Löytyi {len(patent_data)} patenttia")
                p = patents_table(patent_data)

            else:
                st.write("No patent data fetched. Please check your inputs and try again.")

        if 'Julkaisut' in data_type:
            publication_data = get_publication_data(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), [term.strip() for term in terms], token)
            if publication_data and publication_data['data']:  
                st.write(f"Löytyi {publication_data['total']} julkaisua")
                
                publications_data = []

                
                for publication in publication_data['data']:
                    source_publisher = publication.get('source', {}).get('publisher', 'Not available') if publication.get('source') else 'Not available'
                    publication_info = {
                        #'lens_id': publication['lens_id'],
                        #'title': publication['title'],
                        'DOI': None,
                        #'OpenAlex': None,
                        'Publish date': publication['date_published'].split('T')[0],
                        'PDF URL': None,
                        #'Other URL': None,
                        'Publisher': source_publisher,  
                        'Is Open Access': publication.get('is_open_access', False)  
                    }

                    for external_id in publication.get('external_ids', []):
                        if external_id['type'] == 'doi':
                            publication_info['DOI'] = external_id['value']
                        elif external_id['type'] == 'openalex':
                            publication_info['OpenAlex'] = external_id['value']

                    for source_url in publication.get('source_urls', []):
                        if source_url['type'] == 'pdf':
                            publication_info['PDF URL'] = source_url['url']
                        else:  
                            publication_info['Other URL'] = source_url['url']

                    publications_data.append(publication_info)

                publications_df = pd.DataFrame(publications_data)
                #publications_df = publications_df.sort_values(by='Publish date', ascending=False)
                publications_df['DOI'] = 'https://doi.org/'+publications_df['DOI']
                publications_df = publications_df[['Publish date','DOI', 'PDF URL', 'Publisher', 'Is Open Access']]
                publications_df['DOI'] = publications_df['DOI'].apply(lambda x: f"[DOI]({x})")
                publications_df['PDF URL'] = publications_df['PDF URL'].apply(lambda x: f"[PDF]({x})" if x else "")
                
                markdown_table = publications_df.to_markdown(index=False)

                st.markdown(markdown_table)
    
            else:
                st.write("No publication data fetched. Please check your inputs and try again.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
