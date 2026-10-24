"""
LazySort – AI File Organizer
Modern Streamlit web interface for semantic file organization powered by Ollama.
"""

from pathlib import Path
import os
import sys
import pandas as pd
import streamlit as st

# Ensure project root is in python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.extractor import extract_file_content, format_file_size, ALL_SUPPORTED_EXTENSIONS
from core.ollama_client import OllamaClient, OllamaConnectionError, OllamaModelNotFoundError, OllamaError
from core.classifier import SemanticClassifier, DEFAULT_CATEGORIES, CATEGORY_DESCRIPTIONS
from core.organizer import SafeOrganizer, ProposedAction, resolve_collision_path
from core.demo_data import generate_sample_dataset


# --- Page Configuration ---
st.set_page_config(
    page_title="LazySort – AI File Organizer",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Modern Custom Styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: white;
        padding: 1.8rem 2.2rem;
        border-radius: 16px;
        margin-bottom: 1.8rem;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .main-header h1 {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin-bottom: 0.3rem;
        color: #F8FAFC;
    }

    .main-header p {
        font-size: 1rem;
        color: #94A3B8;
        margin-bottom: 0;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
    }

    .status-badge.online {
        background-color: #DCFCE7;
        color: #166534;
        border: 1px solid #86EFAC;
    }

    .status-badge.offline {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #FCA5A5;
    }

    .status-badge.demo {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FCD34D;
    }

    .metric-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.1rem 1.4rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-card .label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin-bottom: 0.3rem;
    }
    .metric-card .val {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0F172A;
    }

    .category-tag {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .tag-finance { background-color: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }
    .tag-work { background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
    .tag-education { background-color: #F5F3FF; color: #6D28D9; border: 1px solid #DDD6FE; }
    .tag-documents { background-color: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
    .tag-images { background-color: #FDF2F8; color: #BE185D; border: 1px solid #FBCFE8; }
    .tag-others { background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; }

    .callout-box {
        background: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 1rem 1.2rem;
        border-radius: 0 10px 10px 0;
        margin-bottom: 1.2rem;
        font-size: 0.92rem;
        color: #334155;
    }
    .callout-box.warning {
        border-left-color: #F59E0B;
        background: #FFFBEB;
    }
    .callout-box.success {
        border-left-color: #10B981;
        background: #ECFDF5;
    }

    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        transition: all 0.15s ease-in-out;
    }
</style>
""", unsafe_allow_html=True)


# --- Initialize Session State ---
if "organizer" not in st.session_state:
    st.session_state.organizer = SafeOrganizer()

if "scan_results" not in st.session_state:
    st.session_state.scan_results = []  # List of ExtractedContent + ClassificationResult

if "proposed_actions" not in st.session_state:
    st.session_state.proposed_actions = []  # List of ProposedAction

if "last_batch_result" not in st.session_state:
    st.session_state.last_batch_result = None

if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = True  # Default to Safe Demo Mode for beginner safety

if "source_folder" not in st.session_state:
    st.session_state.source_folder = str(ROOT_DIR / "sample_files")

if "dest_folder" not in st.session_state:
    st.session_state.dest_folder = str(ROOT_DIR / "organized")


# --- Sidebar Navigation & Settings ---
with st.sidebar:
    st.markdown("### ⚙️ System Settings")

    # Mode Selector
    demo_toggle = st.toggle(
        "🛡️ Safe Demo Mode",
        value=st.session_state.demo_mode,
        help="Test LazySort safely without needing Ollama running or downloading models.",
    )
    st.session_state.demo_mode = demo_toggle

    st.markdown("---")
    st.markdown("### 🧠 Ollama AI Engine")

    ollama_url = st.text_input(
        "Ollama Server URL",
        value="http://localhost:11434",
        help="Default local address where Ollama runs.",
    )
    client = OllamaClient(base_url=ollama_url)

    # Health Check
    health = client.check_health()
    if health["ok"]:
        st.markdown(
            f'<div class="status-badge online">● Ollama Connected (v{health["version"]})</div>',
            unsafe_allow_html=True,
        )
        try:
            available_models = client.list_models()
        except Exception:
            available_models = []
    else:
        st.markdown(
            '<div class="status-badge offline">● Ollama Offline</div>',
            unsafe_allow_html=True,
        )
        available_models = []

    # Model Selection
    default_index = 0
    model_options = available_models if available_models else ["llama3.2", "mistral", "phi3", "llava"]
    if "llama3.2:latest" in model_options:
        default_index = model_options.index("llama3.2:latest")
    elif "llama3.2" in model_options:
        default_index = model_options.index("llama3.2")

    selected_model = st.selectbox(
        "Classification Model",
        options=model_options,
        index=default_index,
        help="Select an open-weight model from your local Ollama library.",
    )

    is_vision = client.is_vision_capable(selected_model)
    if is_vision:
        st.caption("👁️ Vision Model Detected: Image content analysis supported.")
    else:
        st.caption("📝 Text-only Model: Images will be categorized by format into 'Images'.")

    st.markdown("---")
    st.markdown("### 📁 File Safety Operation")
    action_mode = st.radio(
        "Action Type",
        options=["COPY", "MOVE"],
        format_func=lambda x: "Copy Files (Safest - Keeps Originals)" if x == "COPY" else "Move Files (Relocates Originals)",
        index=0,
        help="COPY leaves your original files untouched. MOVE relocates files to their destination categories.",
    )

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size: 0.8rem; color: #64748B;">
            <b>LazySort v1.0</b><br>
            Privacy First: Zero document content logging.<br>
            Collision Guard Active: Files never overwritten.
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- Main Header ---
badge_html = (
    '<span class="status-badge demo">🛡️ SAFE DEMO MODE ACTIVE</span>'
    if st.session_state.demo_mode
    else (
        '<span class="status-badge online">⚡ REAL OLLAMA AI ACTIVE</span>'
        if health["ok"]
        else '<span class="status-badge offline">⚠️ OLLAMA OFFLINE</span>'
    )
)

st.markdown(
    f"""
    <div class="main-header">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <h1>🗂️ LazySort – AI File Organizer</h1>
                <p>Beginner-friendly semantic organizer powered by open-weight AI models & Ollama.</p>
            </div>
            <div>
                {badge_html}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- Tabs ---
tab_organize, tab_demo, tab_history, tab_diagnostics = st.tabs([
    "📂 Organize Files",
    "🧪 Demo & Sample Files",
    "📜 History & Rollback",
    "🛠️ Diagnostics & Setup Guide",
])


# ==============================================================================
# TAB 1: ORGANIZE FILES
# ==============================================================================
with tab_organize:
    # Notice for offline Ollama when in AI mode
    if not st.session_state.demo_mode and not health["ok"]:
        st.error(
            "⚠️ Ollama is currently unreachable at http://localhost:11434. "
            "Please start Ollama in PowerShell (`ollama serve`) or toggle **Safe Demo Mode** in the sidebar."
        )

    # Step 1: Folder Selection
    st.markdown("#### 1. Select Folders")
    col_src, col_dst = st.columns(2)

    with col_src:
        source_dir_str = st.text_input(
            "Source Folder (Files to Organize)",
            value=st.session_state.source_folder,
            help="Folder containing disorganized documents, PDFs, DOCX, or images.",
        )
        st.session_state.source_folder = source_dir_str

    with col_dst:
        dest_dir_str = st.text_input(
            "Destination Folder (Organized Library)",
            value=st.session_state.dest_folder,
            help="Root directory where category folders (Finance, Work, etc.) will be created.",
        )
        st.session_state.dest_folder = dest_dir_str

    src_path = Path(source_dir_str)
    dst_path = Path(dest_dir_str)

    # Check if sample files exist; if not, provide a quick create button
    if not src_path.exists() and "sample_files" in source_dir_str:
        st.info("The sample files directory has not been populated yet. Click below to generate it instantly.")
        if st.button("✨ Generate Sample Files Now", type="secondary"):
            generate_sample_dataset(src_path)
            st.success(f"Created 8 sample documents in '{src_path}'!")
            st.rerun()

    # Step 2: Scan & Classify Trigger
    st.markdown("#### 2. Scan & Semantic Classification")
    scan_col1, scan_col2, scan_col3 = st.columns([2, 1, 1])

    with scan_col1:
        can_scan = src_path.exists() and (st.session_state.demo_mode or health["ok"])
        btn_label = "🔍 Scan & Classify Files (Dry-Run Preview)"
        if st.button(btn_label, type="primary", disabled=not can_scan, use_container_width=True):
            file_candidates = [
                p for p in src_path.iterdir()
                if p.is_file() and not p.name.startswith(".")
            ]

            if not file_candidates:
                st.warning(f"No files found in source folder '{src_path}'.")
            else:
                progress_bar = st.progress(0, text="Initializing file scan...")
                classifier = SemanticClassifier(ollama_client=client)
                organizer: SafeOrganizer = st.session_state.organizer

                results = []
                for idx, file_path in enumerate(file_candidates):
                    progress_text = f"Processing ({idx+1}/{len(file_candidates)}): {file_path.name}"
                    progress_bar.progress((idx + 1) / len(file_candidates), text=progress_text)

                    # Extract Content
                    extracted = extract_file_content(file_path)

                    # Classify
                    classification = classifier.classify_file(
                        extracted=extracted,
                        model_name=selected_model,
                        demo_mode=st.session_state.demo_mode,
                    )
                    results.append((extracted, classification))

                progress_bar.empty()
                st.session_state.scan_results = results

                # Generate Proposals
                classifications_only = [res[1] for res in results]
                st.session_state.proposed_actions = organizer.plan_organization(
                    classifications=classifications_only,
                    destination_root=dst_path,
                )
                st.success(f"Scan complete! Analyzed {len(results)} files. Review the proposed preview below.")

    with scan_col2:
        if st.button("🔄 Refresh View", use_container_width=True):
            st.rerun()

    with scan_col3:
        if st.session_state.scan_results:
            if st.button("🧹 Clear Results", use_container_width=True):
                st.session_state.scan_results = []
                st.session_state.proposed_actions = []
                st.rerun()

    # Step 3: Interactive Proposed Preview
    if st.session_state.proposed_actions:
        st.markdown("---")
        st.markdown("#### 3. Review Proposed Preview (No Files Modified Yet)")

        # Summary Metrics
        proposals: list[ProposedAction] = st.session_state.proposed_actions
        cat_counts = {}
        for p in proposals:
            cat_counts[p.proposed_category] = cat_counts.get(p.proposed_category, 0) + 1

        cols = st.columns(len(DEFAULT_CATEGORIES))
        for i, cat in enumerate(DEFAULT_CATEGORIES):
            with cols[i]:
                count = cat_counts.get(cat, 0)
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="label">{cat}</div>
                        <div class="val">{count}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="callout-box">
                <b>💡 Safe Preview Active:</b> You can adjust proposed categories or uncheck any file before confirmation.
                Files are strictly moved or copied ONLY when you click the confirmation button below.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Interactive Table with Category Overrides
        for idx, item in enumerate(proposals):
            with st.container():
                c_check, c_name, c_cat, c_dest, c_reason = st.columns([0.6, 2.5, 2.0, 3.0, 3.5])

                with c_check:
                    item.is_selected = st.checkbox(
                        "Select",
                        value=item.is_selected,
                        key=f"sel_{idx}_{item.file_name}",
                        label_visibility="collapsed",
                    )

                with c_name:
                    st.markdown(f"**{item.file_name}**")
                    size_str = format_file_size(item.file_path.stat().st_size) if item.file_path.exists() else "0 B"
                    st.caption(f"Size: {size_str} | Ext: `{item.file_path.suffix}`")

                with c_cat:
                    current_cat_idx = (
                        DEFAULT_CATEGORIES.index(item.proposed_category)
                        if item.proposed_category in DEFAULT_CATEGORIES
                        else 0
                    )
                    new_cat = st.selectbox(
                        "Category",
                        options=DEFAULT_CATEGORIES,
                        index=current_cat_idx,
                        key=f"cat_{idx}_{item.file_name}",
                        label_visibility="collapsed",
                    )
                    if new_cat != item.proposed_category:
                        item.proposed_category = new_cat
                        item.target_dir = dst_path / new_cat
                        item.proposed_destination = resolve_collision_path(item.target_dir, item.file_name)

                with c_dest:
                    st.code(str(item.proposed_destination), language="text")

                with c_reason:
                    st.markdown(f"<small>{item.reason}</small>", unsafe_allow_html=True)

                st.markdown("<hr style='margin: 0.4rem 0; border: none; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)

        # Step 4: Explicit Confirmation Stage
        st.markdown("#### 4. Explicit Confirmation & Execution")
        selected_count = sum(1 for p in proposals if p.is_selected)

        st.markdown(
            f"""
            <div class="callout-box warning">
                <b>Confirmation Required:</b> You have selected <b>{selected_count}</b> out of <b>{len(proposals)}</b> files 
                to be <b>{action_mode}ED</b> into <code>{dst_path}</code>.
            </div>
            """,
            unsafe_allow_html=True,
        )

        confirm_checkbox = st.checkbox(
            "✅ I have reviewed the preview above and explicitly authorize LazySort to organize these files.",
            value=False,
            help="Safety check required to prevent unintended file operations.",
        )

        col_exec, _ = st.columns([2, 3])
        with col_exec:
            execute_button = st.button(
                f"🚀 Confirm & {action_mode.capitalize()} {selected_count} Files",
                type="primary",
                disabled=not confirm_checkbox or selected_count == 0,
                use_container_width=True,
            )

        if execute_button:
            organizer: SafeOrganizer = st.session_state.organizer
            with st.spinner(f"{action_mode.capitalize()}ing files with collision protection..."):
                batch_res = organizer.execute_batch(
                    proposals=proposals,
                    action_mode=action_mode,
                )
                st.session_state.last_batch_result = batch_res

            if batch_res.fail_count == 0:
                st.success(
                    f"🎉 Successfully organized {batch_res.success_count} files! (Batch ID: `{batch_res.batch_id}`)"
                )
            else:
                st.warning(
                    f"Completed with partial results: {batch_res.success_count} succeeded, {batch_res.fail_count} failed."
                )

            # Results summary table
            res_data = []
            for r in batch_res.records:
                res_data.append({
                    "File": Path(r.source_path).name,
                    "Action": r.action_type,
                    "Destination": r.destination_path,
                    "Status": r.status,
                    "Error": r.error_message or "None",
                })
            st.dataframe(pd.DataFrame(res_data), use_container_width=True)


# ==============================================================================
# TAB 2: DEMO & SAMPLE FILES
# ==============================================================================
with tab_demo:
    st.markdown("### 🧪 Safe Demo Mode & Test Dataset")
    st.markdown(
        """
        LazySort includes a realistic demo dataset generator so you can test all features 
        (PDF extraction, DOCX parsing, Image handling, collision avoidance, and batch undo) 
        **before** downloading Ollama or AI weights.
        """
    )

    col_d1, col_d2 = st.columns([1, 1])

    with col_d1:
        st.markdown("#### Generate Sample Files")
        st.write(
            "This will create 8 authentic test files in `sample_files/` covering all categories:\n"
            "- **Finance**: `Quarterly_Tax_Invoice_2026.pdf`, `Coffee_Shop_Receipt.txt`\n"
            "- **Work**: `Senior_Software_Engineer_Resume.docx`\n"
            "- **Education**: `Algorithms_Lecture_04_Notes.txt`, `Machine_Learning_Course_Syllabus.docx`\n"
            "- **Documents**: `Commercial_Office_Lease_Agreement.pdf`\n"
            "- **Images**: `System_Architecture_Diagram.png`\n"
            "- **Others**: `application_runtime_config.json`"
        )

        if st.button("📦 (Re)Generate Demo Files in sample_files/", type="primary"):
            created = generate_sample_dataset(ROOT_DIR / "sample_files")
            st.success(f"Generated {len(created)} authentic sample files in `{ROOT_DIR / 'sample_files'}`!")
            st.session_state.source_folder = str(ROOT_DIR / "sample_files")
            st.rerun()

    with col_d2:
        st.markdown("#### Current Sample Files Status")
        sample_dir = ROOT_DIR / "sample_files"
        if sample_dir.exists():
            files = list(sample_dir.glob("*.*"))
            if files:
                st.write(f"Found **{len(files)}** files in `{sample_dir.name}/`:")
                file_summary = []
                for f in files:
                    file_summary.append({
                        "Name": f.name,
                        "Type": f.suffix,
                        "Size": format_file_size(f.stat().st_size),
                    })
                st.dataframe(pd.DataFrame(file_summary), use_container_width=True)
            else:
                st.info("The sample directory exists but is empty. Click generate to populate it.")
        else:
            st.info("Sample directory does not exist yet. Click the button to create it.")


# ==============================================================================
# TAB 3: HISTORY & ROLLBACK
# ==============================================================================
with tab_history:
    st.markdown("### 📜 Operation Audit Log & Rollback")
    st.markdown(
        """
        <div class="callout-box">
            <b>🛡️ Privacy Guarantee:</b> The audit log records timestamps, source/destination file paths, 
            and byte sizes. <b>No sensitive document contents, text snippets, or personal data are ever written to the log.</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    organizer: SafeOrganizer = st.session_state.organizer
    history = organizer.get_audit_history()

    if not history:
        st.info("No file operations recorded yet. Organize some files to see their history here.")
    else:
        # Rollback Section
        st.markdown("#### ⏪ Undo an Operation Batch")
        # Extract unique batch IDs from history
        unique_batches = list(dict.fromkeys(
            r.get("batch_id") for r in reversed(history)
            if r.get("batch_id") and not r.get("batch_id", "").startswith("undo_")
        ))

        if unique_batches:
            c_batch, c_undo = st.columns([2, 1])
            with c_batch:
                selected_batch = st.selectbox(
                    "Select Batch ID to Revert",
                    options=unique_batches,
                    help="Rolls back moved files to their original folder or removes copied files.",
                )
            with c_undo:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("⏪ Undo Selected Batch", type="secondary", use_container_width=True):
                    undo_result = organizer.undo_batch(selected_batch)
                    if undo_result["ok"]:
                        st.success(f"Successfully reverted {undo_result['undone_count']} files from batch `{selected_batch}`!")
                        st.rerun()
                    else:
                        st.error(f"Failed to revert some files: {undo_result['errors']}")

        st.markdown("#### Audit Records")
        df_hist = pd.DataFrame(history)
        st.dataframe(df_hist, use_container_width=True)


# ==============================================================================
# TAB 4: DIAGNOSTICS & SETUP GUIDE
# ==============================================================================
with tab_diagnostics:
    st.markdown("### 🛠️ Ollama Diagnostics & Windows PowerShell Setup")
    
    col_stat1, col_stat2 = st.columns(2)

    with col_stat1:
        st.markdown("#### Ollama Service Status")
        diag_health = client.check_health()
        if diag_health["ok"]:
            st.success(f"✅ Ollama service is running (API Version: {diag_health['version']})")
            models = client.list_models()
            st.write(f"**Installed Models ({len(models)}):**")
            for m in models:
                v_flag = "👁️ Vision" if client.is_vision_capable(m) else "📝 Text"
                st.markdown(f"- `{m}` ({v_flag})")
        else:
            st.error("❌ Ollama service is NOT responding on http://localhost:11434")
            st.write(f"Details: `{diag_health['error']}`")

    with col_stat2:
        st.markdown("#### Quick AI Ping Test")
        st.write("Send a live test prompt to verify that your selected Ollama model is operating properly.")
        test_model = st.selectbox("Test Model", options=model_options, key="diag_model_select")
        
        if st.button("⚡ Test Model Ping", disabled=not diag_health["ok"]):
            with st.spinner(f"Sending prompt to {test_model}..."):
                try:
                    resp = client.generate(
                        model=test_model,
                        prompt="Categorize this document snippet: 'Invoice #1024. Balance due: $350.00 USD.' into: Finance, Work, Education, Documents, Images, Others.",
                        format_json=True,
                    )
                    st.success("Ollama responded successfully!")
                    st.code(resp, language="json")
                except OllamaError as e:
                    st.error(f"Ollama Error: {str(e)}")

    st.markdown("---")
    st.markdown("### 📋 Step-by-Step Setup Guide (Windows PowerShell)")
    st.markdown(
        """
        Follow these beginner-friendly steps to run Ollama and LazySort together:

        #### Step 1: Install Ollama on Windows
        1. Download the official installer from [https://ollama.com/download](https://ollama.com/download).
        2. Run `OllamaSetup.exe` and follow the on-screen installer.
        3. Once installed, Ollama will run in your Windows system tray.

        #### Step 2: Download Recommended Open-Weight Models
        Open a new **Windows PowerShell** terminal and pull the models:
        ```powershell
        # 1. Pull Llama 3.2 (fast, lightweight 2GB model - recommended for documents):
        ollama pull llama3.2

        # 2. (Optional) Pull LLaVA if you want vision classification for photos and receipts:
        ollama pull llava
        ```

        #### Step 3: Verify Ollama is Serving
        ```powershell
        # Test that Ollama is responding
        curl http://localhost:11434/api/version
        ```

        #### Step 4: Run LazySort
        ```powershell
        # From the d:\\lazysort folder:
        streamlit run app.py
        ```
        Then disable **Safe Demo Mode** in the sidebar to activate the real AI model!
        """
    )
