"""Streamlit web app for interactive Brave Search ingestion and pipeline runs.

Flow:
- User enters a brand or query.
- The app queries Brave for up to 10 URL suggestions.
- The user checks/selects up to 10 results.
- The app fetches the selected pages and runs the existing pipeline (normalization, scoring, reporting) synchronously.

Usage:
    streamlit run webapp/app.py

Note: This app calls blocking code; for production consider running pipeline tasks in a background worker.
"""
from __future__ import annotations

import sys
import os
# Ensure project root is on PYTHONPATH so imports like `from ingestion import brave_search`
# work when Streamlit runs with the working directory set to `webapp/`.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tempfile
import threading
import time
import json
import os
from typing import List
import functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


# Keep references to local file servers so they don't get garbage-collected.
_LOCAL_SERVERS: dict = {}


def _start_local_file_server(directory: str) -> str:
    """Start a simple HTTP file server serving `directory` and return the base URL.

    The server is started in a background thread and registered in the
    `_LOCAL_SERVERS` dict keyed by directory.
    """
    if directory in _LOCAL_SERVERS:
        return _LOCAL_SERVERS[directory]['url']

    class _Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
        def log_message(self, format, *args):
            # Override to silence noisy HTTP logs (keeps console clean while polling)
            return
        def end_headers(self):
            # Add permissive CORS headers so the browser component can poll the local
            # file server without running into cross-origin restrictions.
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()

        def do_OPTIONS(self):
            # Respond to CORS preflight requests
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

    # Bind to localhost on an ephemeral port
    server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
    host, port = server.server_address
    url = f'http://{host}:{port}'

    def _serve():
        try:
            server.serve_forever()
        except Exception:
            pass

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()

    _LOCAL_SERVERS[directory] = {'server': server, 'thread': thread, 'url': url}
    return url

from ingestion import brave_search
from scripts.run_pipeline import run_pipeline_for_contents

# NOTE: UI content is defined in main() so importing this module for tests
# does not execute Streamlit UI code. Use `streamlit run webapp/app.py` to
# start the interactive UI which calls main().

# Module-level UI removed. Use main() for Streamlit runs. Helpers remain importable.


def search_brave_results(query: str, num: int = 10):
    """Programmatic search wrapper for tests and other callers."""
    return brave_search.search_brave(query, size=num)


def programmatic_quick_run(selected_urls: list, output_dir: str | None = None, brand_id: str | None = None, sources: list | None = None, keywords: list | None = None, include_comments: bool | None = None):
    """Run the pipeline for a list of URLs programmatically (used in tests).

    Returns the dict produced by `run_pipeline_for_contents`.
    """
    # Default args
    od = output_dir or './output'
    bid = brand_id or 'brand'
    return run_pipeline_for_contents(selected_urls, output_dir=od, brand_id=bid, sources=sources, keywords=keywords, include_comments=include_comments)


def main():
    """Entrypoint for the Streamlit app. Separated so importing this module doesn't execute UI code."""
    import streamlit as st  # re-import locally to keep top-level import lightweight for tests

    st.set_page_config(page_title="AR Pipeline Quick Run", layout="wide")

    st.title("AR Pipeline WIP")

    # --- Progress indicator (visible while pipeline is running or when marker exists) ---
    marker_exists = False
    marker = st.session_state.get('marker')
    if marker and os.path.exists(marker):
        marker_exists = True

    if st.session_state.get('run_pending') or marker_exists:
        # Top-level container so progress is hard to miss
        prog_container = st.container()
        with prog_container:
            st.markdown("## Pipeline status")
            st.info("Run in progress — getting results. The page will update when finished.")

            # Maintain a lightweight progress counter in session state so the bar moves
            progress_key = '_progress_counter'
            if progress_key not in st.session_state or st.session_state.get(progress_key) >= 95:
                st.session_state[progress_key] = 5
            else:
                st.session_state[progress_key] = min(95, st.session_state[progress_key] + 10)

            # Show progress both in-page and in the sidebar for visibility
            st.progress(st.session_state[progress_key])
            try:
                st.sidebar.progress(st.session_state[progress_key])
            except Exception:
                # Some environments may not support sidebar; ignore failures
                pass

            # Attempt a guarded auto-refresh in environments that support it so the
            # UI re-renders and the progress bar updates. Do not fail if the API
            # is not available.
            try:
                rerun_fn = getattr(st, 'experimental_rerun', None)
                if callable(rerun_fn):
                    # Call experimental_rerun in a try/except to avoid crashes
                    try:
                        rerun_fn()
                    except Exception:
                        # If rerun fails, fall back to passive progress updates
                        pass
            except Exception:
                # Defensive: ignore any unexpected errors here
                pass

            # If the run marker already exists, load and display results immediately
            if marker_exists:
                try:
                    with open(marker, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                    st.success('Run finished — results loaded below')
                    st.write(data)
                    # clear pending state
                    st.session_state['run_pending'] = False
                except Exception as e:
                    st.error(f'Failed to read run result: {e}')

            # Action buttons
            cols = st.columns([1, 1, 2])
            with cols[0]:
                if st.button('Refresh now'):
                    # Check if marker file exists and show results if present
                    if marker and os.path.exists(marker):
                        try:
                            with open(marker, 'r', encoding='utf-8') as fh:
                                data = json.load(fh)
                            st.success('Run finished — results loaded below')
                            st.write(data)
                            # clear pending state
                            st.session_state['run_pending'] = False
                        except Exception as e:
                            st.error(f'Failed to read run result: {e}')
                    else:
                        st.info('No result yet; still running.')
            with cols[1]:
                if st.button('Open output dir'):
                    td = st.session_state.get('tmpdir')
                    if td and os.path.isdir(td):
                        st.write(f'Output directory: {td}')
                    else:
                        st.info('Output directory not available yet.')
            with cols[2]:
                st.write('')

        # Inject a component that polls the local file server for the run
        # result using fetch() and updates the page when the result is ready.
        try:
            import streamlit.components.v1 as components
            server_url = st.session_state.get('_run_server_url')
            if server_url and st.session_state.get('run_pending'):
                js = f"""
                <div id='ar_run_result_container'></div>
                <script>
                if (!window._ar_fetch_installed) {{
                    window._ar_fetch_installed = true;
                    const url = '{server_url}/_run_result.json';
                    const poll = setInterval(async function() {{
                        try {{
                            const r = await fetch(url, {{ method: 'HEAD' }});
                            if (r.ok) {{
                                // result exists, fetch it and insert into page
                                const res = await fetch(url);
                                const data = await res.json();
                                const container = document.getElementById('ar_run_result_container');
                                container.innerText = JSON.stringify(data, null, 2);
                                clearInterval(poll);
                                // Optionally trigger a soft reload
                                // window.location.reload();
                            }}
                        }} catch (e) {{
                            // ignore network errors while polling
                        }}
                    }}, 3000);
                }}
                </script>
                """
                components.html(js, height=200)
        except Exception:
            pass

        st.divider()

    query = st.text_input("Brand or search query", value="nike", key='brand_query')
    num = st.number_input("Max search results to fetch", min_value=1, max_value=20, value=10, step=1, key='max_results')
    # Source selection
    st.write('Include additional sources in this run:')
    include_reddit = st.checkbox('Reddit', value=False, key='include_reddit')
    include_youtube = st.checkbox('YouTube', value=False, key='include_youtube')
    include_comments = st.checkbox('Include YouTube comments', value=False, key='include_comments')

    if st.button("Search Brave", key='search_brave_btn'):
        with st.spinner("Querying Brave…"):
            results = brave_search.search_brave(query, size=num)
            st.session_state['brave_results'] = results

    # Render stored results (so checkboxes persist)
    results = st.session_state.get('brave_results')
    if results is None:
        # no results yet
        pass
    else:
        if not results:
            st.warning("No results found or Brave search failed.")
        else:
            st.write(f"Found {len(results)} results. Select up to 10 to run through the pipeline.")
            selected = []
            import hashlib

            for i, r in enumerate(results):
                url = r.get('url') or ''
                key_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:10]
                checkbox_key = f"res_{key_hash}"
                check = st.checkbox(f"{r.get('title') or url}", key=checkbox_key)
                st.write(r.get('snippet'))
                if check:
                    selected.append(url)

            if st.button('Clear results', key='clear_results'):
                # remove result and checkbox keys
                if 'brave_results' in st.session_state:
                    del st.session_state['brave_results']
                for k in list(st.session_state.keys()):
                    if k.startswith('res_'):
                        del st.session_state[k]

            if st.button("Run pipeline on selected URLs", key='run_pipeline_btn'):
                if not selected:
                    st.warning("No URLs selected.")
                else:
                    # Credential checks for optional sources
                    missing_creds = []
                    from config.settings import APIConfig
                    cfg = APIConfig()
                    if include_reddit and (not cfg.reddit_client_id or not cfg.reddit_client_secret):
                        missing_creds.append('Reddit (REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET)')
                    if include_youtube and not cfg.youtube_api_key:
                        missing_creds.append('YouTube (YOUTUBE_API_KEY)')
                    if missing_creds:
                        st.error('Missing API credentials for selected sources: ' + ', '.join(missing_creds))
                        st.stop()

                    # Run pipeline in separate thread to avoid blocking Streamlit UI
                    # Use a project-local output directory so results are easy to find
                    runs_root = os.path.join(PROJECT_ROOT, 'output', 'runs')
                    os.makedirs(runs_root, exist_ok=True)
                    ts = int(time.time())
                    tmpdir = os.path.join(runs_root, f"run_{ts}")
                    os.makedirs(tmpdir, exist_ok=True)
                    st.info(f"Running pipeline; output will be saved to {tmpdir}")

                    def _thread_run(urls, outdir, bid, sources_list):
                        try:
                            res = run_pipeline_for_contents(urls, output_dir=outdir, brand_id=bid, sources=sources_list, include_comments=st.session_state.get('include_comments'))
                            # Write atomically to avoid the file being observed while
                            # partially written by the polling client.
                            target = os.path.join(outdir, '_run_result.json')
                            tmp_target = target + '.tmp'
                            with open(tmp_target, 'w', encoding='utf-8') as fh:
                                json.dump(res, fh)
                            os.replace(tmp_target, target)
                        except Exception as e:
                            target = os.path.join(outdir, '_run_result.json')
                            tmp_target = target + '.tmp'
                            with open(tmp_target, 'w', encoding='utf-8') as fh:
                                json.dump({'error': str(e)}, fh)
                            try:
                                os.replace(tmp_target, target)
                            except Exception:
                                pass

                    sources_list = ['brave']
                    if include_reddit:
                        sources_list.append('reddit')
                    if include_youtube:
                        sources_list.append('youtube')

                    thread = threading.Thread(target=_thread_run, args=(selected, tmpdir, query, sources_list))
                    thread.daemon = True
                    thread.start()

                    # Register run in session_state for non-blocking polling
                    st.session_state['run_pending'] = True
                    st.session_state['marker'] = os.path.join(tmpdir, '_run_result.json')
                    st.session_state['tmpdir'] = tmpdir
                    st.info('Pipeline started; this page will refresh when the run completes.')

                    # Start a local file server for the run directory so the
                    # client-side component can poll for the result file without
                    # reloading continuously. Store the server URL in session_state.
                    try:
                        server_url = _start_local_file_server(tmpdir)
                        st.session_state['_run_server_url'] = server_url
                    except Exception:
                        st.session_state['_run_server_url'] = None

                    # Some test environments or Streamlit versions may not support
                    # programmatic rerun. Avoid calling `st.experimental_rerun()`
                    # directly to prevent AttributeError in those environments.
                    # Instead, set a session flag that other parts of the UI can
                    # observe and react to if desired.
                    st.session_state['_needs_rerun'] = True

                    # Inline progress indicator directly below the Run button
                    progress_key = '_progress_counter'
                    if progress_key not in st.session_state or st.session_state.get(progress_key, 0) >= 95:
                        st.session_state[progress_key] = 5
                    else:
                        st.session_state[progress_key] = min(95, st.session_state[progress_key] + 10)

                    with st.container():
                        st.markdown('**Run started — progress**')
                        st.progress(st.session_state[progress_key])
                        if st.button('Refresh now (inline)', key='refresh_inline'):
                            marker = st.session_state.get('marker')
                            if marker and os.path.exists(marker):
                                try:
                                    with open(marker, 'r', encoding='utf-8') as fh:
                                        data = json.load(fh)
                                    st.success('Run finished — results loaded below')
                                    st.write(data)
                                    st.session_state['run_pending'] = False
                                except Exception as e:
                                    st.error(f'Failed to read run result: {e}')
                            else:
                                st.info('No result yet; still running.')


if __name__ == '__main__':
    main()
