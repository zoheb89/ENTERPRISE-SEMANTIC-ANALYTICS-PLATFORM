import streamlit as st
from theme import page_header, section_title, navigate_to
import security_fabric as security
import discovery_engine as discovery

page_header('Databricks Discovery','Live Unity Catalog discovery — catalogs, schemas, tables, columns, relationships and Metric Views.')
if not security.is_configured():
    st.markdown('<div class="platform-banner warn">Databricks is not configured. Add DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID and DATABRICKS_CATALOG to Streamlit Secrets.</div>',unsafe_allow_html=True)
    st.stop()

try:
    catalogs=discovery.list_catalogs()
except Exception as e:
    st.error(f'Unity Catalog discovery failed: {e}'); st.stop()

preferred=st.secrets.get('DATABRICKS_CATALOG','')
idx=catalogs.index(preferred) if preferred in catalogs else 0
catalog=st.selectbox('Catalog',catalogs,index=idx if catalogs else 0)
if st.button('↻ Refresh Discovery',type='primary'):
    st.cache_data.clear(); st.rerun()
if not catalog: st.stop()
try:
    result=discovery.discover_catalog(catalog)
    schemas=result['schemas']; tables=result['tables']; mvs=result['metric_views']
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Schemas',len(schemas)); c2.metric('Relations',len(tables)); c3.metric('Metric Views',len(mvs)); c4.metric('Managed Tables',int((tables['table_type']=='MANAGED').sum()) if not tables.empty else 0)
    st.divider()
    section_title('Metric Views','These are discovered from Databricks — not inferred from C INVENT UI state.')
    if mvs.empty: st.info('No Metric Views are visible to the configured identity in this catalog.')
    else:
        for _,row in mvs.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['full_name']}**  ·  `{row['table_type']}`")
                if st.button('Inspect',key='inspect_'+str(row['full_name'])):
                    st.session_state['discovery_selected_mv']=row['full_name']; st.rerun()
    selected=st.session_state.get('discovery_selected_mv')
    if selected:
        detail=discovery.metric_view_details(selected)
        st.divider(); section_title('Metric View Metadata',selected)
        a,b=st.columns(2); a.write('**Table type:** '+str(detail.get('table_type'))); b.write('**Owner:** '+str(detail.get('owner')))
        if not detail['columns'].empty: st.dataframe(detail['columns'],use_container_width=True,hide_index=True)
    st.divider(); section_title('Unity Catalog Relations','Real tables and views visible to the configured identity.')
    if not tables.empty: st.dataframe(tables[['full_name','table_type','owner','comment']],use_container_width=True,hide_index=True)
    st.divider(); section_title('Schemas'); st.dataframe(schemas,use_container_width=True,hide_index=True)
except Exception as e:
    st.error(f'Discovery error: {e}')
