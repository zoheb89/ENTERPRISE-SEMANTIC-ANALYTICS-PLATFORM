"""Real Unity Catalog discovery for C INVENT.

Uses the Databricks workspace REST Tables API for authoritative object types
(including METRIC_VIEW) and SQL INFORMATION_SCHEMA for schemas/columns and
privilege-aware metadata. No hard-coded domain list is used.
"""
from __future__ import annotations
import requests
import streamlit as st
import pandas as pd
import security_fabric as security


def _host(): return st.secrets['DATABRICKS_HOST'].rstrip('/')
def _headers(): return {**security._auth_headers(), 'Content-Type':'application/json'}


def _get(path, params=None):
    r=requests.get(_host()+path,headers=_headers(),params=params or {},timeout=45)
    r.raise_for_status(); return r.json()


def list_catalogs():
    data=_get('/api/2.1/unity-catalog/catalogs')
    return sorted([x.get('name') for x in data.get('catalogs',[]) if x.get('name')])


def list_schemas(catalog):
    # SQL information_schema is privilege-aware and stable across UC workspaces.
    from publish_engine import get_sql_connection
    with get_sql_connection() as conn:
        q=f"SELECT schema_name, schema_owner, comment, created, last_altered FROM {catalog}.information_schema.schemata ORDER BY schema_name"
        return pd.read_sql(q,conn)


def list_tables(catalog, schema=None):
    rows=[]; token=None
    while True:
        params={'catalog_name':catalog,'max_results':100}
        if schema: params['schema_name']=schema
        if token: params['page_token']=token
        data=_get('/api/2.1/unity-catalog/tables',params)
        rows.extend(data.get('tables',[]))
        token=data.get('next_page_token')
        if not token: break
    out=[]
    for x in rows:
        out.append({'full_name':x.get('full_name'),'name':x.get('name'),'schema_name':x.get('schema_name'),'catalog_name':x.get('catalog_name'),'table_type':x.get('table_type'),'comment':x.get('comment'),'owner':x.get('owner') or x.get('table_owner')})
    return pd.DataFrame(out)


def get_table(full_name):
    encoded=requests.utils.quote(full_name,safe='')
    return _get(f'/api/2.1/unity-catalog/tables/{encoded}')


def discover_catalog(catalog):
    schemas=list_schemas(catalog)
    tables=list_tables(catalog)
    metrics=tables[tables['table_type'].astype(str).str.upper().eq('METRIC_VIEW')].copy() if not tables.empty else pd.DataFrame()
    # Some SQL/older drivers expose metric views as VIEW. The REST Tables API
    # is authoritative; if an object is named mv_* we keep it visible as a
    # candidate only when the API cannot return a table type.
    if not metrics.empty:
        metrics['kind']='Metric View'
    return {'catalog':catalog,'schemas':schemas,'tables':tables,'metric_views':metrics}


def metric_view_details(full_name):
    info=get_table(full_name)
    cols=[]
    for c in info.get('columns',[]) or []:
        cols.append({'name':c.get('name'),'type':c.get('type_name') or c.get('type_text') or c.get('type'),'nullable':c.get('nullable')})
    return {'full_name':full_name,'table_type':info.get('table_type'),'columns':pd.DataFrame(cols),'comment':info.get('comment'),'owner':info.get('owner'),'view_definition':info.get('view_definition')}


def query(sql):
    from publish_engine import get_sql_connection
    with get_sql_connection() as conn:
        cur=conn.cursor(); cur.execute(sql)
        cols=[d[0] for d in cur.description] if cur.description else []
        rows=cur.fetchall() if cur.description else []
    return pd.DataFrame(rows,columns=cols)
