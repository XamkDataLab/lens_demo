import streamlit as st
import pandas as pd
import openai
from hakufunktiot import *
from datanmuokkausfunktiot import *

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
                        value='low carbon concrete, sustainable concrete, green concrete, eco concrete', 
                        height=300).split(',')

st.subheader("Get Synonyms for Search Terms")
if st.button("Get Synonyms"):
    openai.api_key = st.secrets["openai_api_key"]
    try:
        for term in terms:
            term = term.strip()
            response = openai.ChatCompletion.create(
                model="gpt-4-0125-preview",
                messages=[{
                    "role": "system",
                    "content": "You are a helpful assistant."
                }, {
                    "role": "user",
                    "content": f"Give me synonyms or related keywords for: {term}"
                }]
            )
            synonyms = response.choices[0].message['content']
            st.write(f"**{term}**: {synonyms}")
    except Exception as e:
        st.error(f"An error occurred while fetching synonyms: {str(e)}")

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
