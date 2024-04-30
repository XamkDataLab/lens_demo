import streamlit as st
import pandas as pd
from openai import OpenAI
from hakufunktiot import *
from datanmuokkausfunktiot import *
import plotly.graph_objs as go

client = OpenAI(api_key=st.secrets["openai_api_key"])

def get_synonyms(term):
    try:
        chat_completion = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {
                    "role": "user",
                    "content": f"List related search terms and/or synonyms for this search term: '{term}'?"
                }
            ],
        )
        if chat_completion.choices:
            response_content = chat_completion.choices[0].message.content
            return response_content
    except Exception as e:
        st.error(f"An error occurred while fetching related terms: {e}")
        return "Error fetching related terms"

def create_sankey(df, group_descriptions):
   
    filtered_df = df[df['Group Description'].isin(group_descriptions)]
    all_nodes = filtered_df['Group Description'].tolist() + filtered_df['Subgroup Description'].tolist()
    all_nodes = list(dict.fromkeys(all_nodes)) 
    
    node_indices = {node: i for i, node in enumerate(all_nodes)}
    source_indices = [node_indices[group] for group in filtered_df['Group Description']]
    target_indices = [node_indices[subgroup] for subgroup in filtered_df['Subgroup Description']]
    
    values = filtered_df.groupby(['Group Description', 'Subgroup Description']).size().tolist()
    
    sankey = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes,
        ),
        link=dict(
            source=source_indices,
            target=target_indices,
            value=values
        ))])
    
    return sankey

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>Datahaku patenteista ja julkaisuista</h1>", unsafe_allow_html=True)
main_row = st.columns([2, 1, 2]) 

with main_row[0]:
    image_url = 'https://raw.githubusercontent.com/XamkDataLab/lens_demo/main/DALL3.jpg'
    st.image(image_url)

with main_row[1]:
    data_type = st.multiselect('Valitse tietokanta', ['Patentit', 'Julkaisut'], default=['Patentit', 'Julkaisut'])
    start_date = st.date_input('Alkaen', value=pd.to_datetime('2024-01-01'))
    end_date = st.date_input('Päättyen', value=pd.to_datetime('2024-03-01'))

with main_row[2]:
    class_cpc_prefix = st.text_input('CPC-luokitus (patenteille, voi jättää tyhjäksi)', '')
    terms = st.text_area('Hakutermit (erota pilkulla, operaattori OR)', 
                        value='', 
                        height=300).split(',')

if st.button("Get Related Terms"):
    if terms: 
        for term in terms:
            synonyms = get_synonyms(term.strip())
            if synonyms:
                st.write(f"**{term}**: {synonyms}")
            else:
                st.write(f"**{term}**: No related terms found.")
    else:
        st.write("No terms provided.")

token = st.secrets["mytoken"]


if st.button('Hae Data'):
    try:
        if 'Patentit' in data_type:
            st.session_state['patent_data'] = get_patent_data(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), [term.strip() for term in terms], token, class_cpc_prefix or None)
            if st.session_state['patent_data']:
                st.write(f"Löytyi {len(st.session_state['patent_data'])} patenttia")
                p = patents_table(st.session_state['patent_data'])
                c = cpc_classifications_table(st.session_state['patent_data'])
                a = applicants_table(st.session_state['patent_data'])
                st.session_state['c'] = make_cpc(c, 'cpc_ultimate_titles.json')
                st.dataframe(p)
                st.dataframe(st.session_state['c'])
                
            else:
                st.write("No patent data fetched. Please check your inputs and try again.")

        if 'Julkaisut' in data_type:
            st.session_state['publication_data'] = get_publication_data(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), [term.strip() for term in terms], token)
            if st.session_state['publication_data'] and st.session_state['publication_data']['data']:  
                st.write(f"Löytyi {st.session_state['publication_data']['total']} julkaisua")
                
                publications_data = []

                for publication in st.session_state['publication_data']['data']:
                    source_publisher = publication.get('source', {}).get('publisher', 'Not available') if publication.get('source') else 'Not available'
                    publication_info = {
                        'Publish date': publication['date_published'].split('T')[0],
                        'Publisher': source_publisher,  
                        'Is Open Access': publication.get('is_open_access', False)  
                    }

                    if 'doi' in publication.get('external_ids', {}):
                        publication_info['DOI'] = 'https://doi.org/' + publication['external_ids']['doi']

                    if 'pdf' in publication.get('source_urls', {}):
                        publication_info['PDF URL'] = f"[PDF]({publication['source_urls']['pdf']})"
                    else:
                        publication_info['PDF URL'] = ""

                    publications_data.append(publication_info)

                publications_df = pd.DataFrame(publications_data)
                publications_df = publications_df[['Publish date', 'DOI', 'PDF URL', 'Publisher', 'Is Open Access']]
                
                markdown_table = publications_df.to_markdown(index=False)
                st.markdown(markdown_table)
    
            else:
                st.write("No publication data fetched. Please check your inputs and try again.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if 'c' in st.session_state:
    group_descriptions = st.multiselect('Select Group Descriptions', options=st.session_state['c']['Group Description'].unique(), key='group_selection')
    if group_descriptions:
        if st.button("Show Sankey Diagram"):
            sankey_figure = create_sankey(st.session_state['c'], group_descriptions)
            st.plotly_chart(sankey_figure)
