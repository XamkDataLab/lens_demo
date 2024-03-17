import streamlit as st

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>Datahaku patenteista ja julkaisuista</h1>", unsafe_allow_html=True)

main_col1, main_col2 = st.columns([2, 2])

with main_col1:
    st.image("DALL.png")

with main_col2:
    # Adjust the proportion of the columns to give more space to the selectors
    col1, col2 = st.columns([2, 3])

    with col1:
        # All selectors in the same column for more room
        data_type = st.multiselect('Valitse tietokanta', ['Patentit', 'Julkaisut'], default=['Patentit', 'Julkaisut'])
        start_date = st.date_input('Alkaen', value=pd.to_datetime('2024-01-01'))
        end_date = st.date_input('Päättyen', value=pd.to_datetime('2024-03-01'))
        class_cpc_prefix = st.text_input('CPC luokitus (voi jättää tyhjäksi)', '')

    with col2:
        # Slightly narrower search terms box
        terms = st.text_area('Hakutermit (erota pilkulla, operaattori OR)', 
                             value='low carbon concrete, sustainable concrete, green concrete, eco concrete', 
                             height=300).split(',')

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
                    publication_info = {
                        #'lens_id': publication['lens_id'],
                        #'title': publication['title'],
                        'DOI': None,
                        #'OpenAlex': None,
                        'PDF URL': None,
                        #'Other URL': None,
                        'Publisher': publication['source'].get('publisher', 'Not available'),  
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
                publications_df['DOI'] = 'https://doi.org/'+publications_df['DOI']
                publications_df = publications_df[['DOI', 'PDF URL', 'Publisher', 'Is Open Access']]
                # Convert URLs to Markdown links
                publications_df['DOI'] = publications_df['DOI'].apply(lambda x: f"[DOI]({x})")
                publications_df['PDF URL'] = publications_df['PDF URL'].apply(lambda x: f"[PDF]({x})" if x else "")

                
                # Convert the DataFrame to a Markdown string
                markdown_table = publications_df.to_markdown(index=False)

                # Print the Markdown table string (or use st.markdown in a Streamlit app)
                st.markdown(markdown_table)
                
                #st.dataframe(publications_df)  # Display the processed publication data as a DataFrame
            else:
                st.write("No publication data fetched. Please check your inputs and try again.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
