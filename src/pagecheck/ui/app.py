"""Shell inicial da interface; não implementa auditorias fictícias."""
import os

import httpx
import streamlit as st


def render_app() -> None:
    st.set_page_config(page_title='Page Check', page_icon='🔎', layout='wide')
    st.title('Page Check')
    st.caption('Auditoria técnica e visual de landing pages para marketing e GTM.')

    api_url = os.getenv('PAGECHECK_API_URL', 'http://127.0.0.1:8000').rstrip('/')
    try:
        response = httpx.get(f'{api_url}/health', timeout=2.0)
        response.raise_for_status()
        if response.json().get('status') == 'ok':
            st.success('Conexão com a FastAPI: funcionando.')
        else:
            st.warning('A API respondeu, mas o status de saúde é inesperado.')
    except (httpx.HTTPError, ValueError):
        st.warning('FastAPI indisponível. Inicie o servidor em outro terminal.')

    st.info('Estrutura inicial pronta. A auditoria de URLs ainda será implementada nas próximas etapas.')
