# 🗂️ LazySort – AI File Organizer

> A beginner-friendly, privacy-focused file organizer that classifies your messy folders into organized categories using open-weight AI models running locally on your computer via **Ollama**.

---

## 🌟 Features at a Glance

- **Clean Web Interface**: Built with Python and Streamlit for an intuitive visual experience.
- **Genuine Local AI Classification**: Uses open-weight models through Ollama (`llama3.2`, `mistral`, `phi3`, `llava`). No cloud APIs, no data leaves your machine, no faked results.
- **Multi-Format Extraction**:
  - **PDF Documents** (`.pdf`) via `pypdf`.
  - **Word Documents** (`.docx`) via `python-docx`.
  - **Plain Text & Code** (`.txt`, `.md`, `.csv`, `.json`, `.py`, `.log`).
  - **Images** (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`): Supports vision models (like `llava`) or clearly reports image analysis limits when using text-only models.
- **6 Useful Semantic Categories**:
  - 💳 **Finance**: Invoices, receipts, tax documents, bank statements, bills.
  - 💼 **Work**: Resumes, contracts, project specs, meeting minutes.
  - 🎓 **Education**: Lecture notes, study guides, homework, textbooks, syllabus.
  - 📄 **Documents**: Certificates, identity papers, letters, official forms.
  - 🖼️ **Images**: Photos, diagrams, screenshots, artwork.
  - 📦 **Others**: Code scripts, archives, configs, unclassified files.
- **Dry-Run Preview & Explicit Confirmation**:
  - Never moves or alters files without your review.
  - Interactive preview table with manual category overrides.
  - Requires explicit checkbox confirmation before taking action.
- **Non-Destructive Safety & Collision Guard**:
  - Default **Copy Mode** keeps your original files completely safe.
  - Automatic collision prevention: if `invoice.pdf` exists, creates `invoice (1).pdf` instead of overwriting.
  - **Batch Undo / Rollback**: 1-click restore to reverse any batch.
- **Zero Document Logging**:
  - Audit logs record timestamps, file sizes, and paths only. Document contents or sensitive extracts are **never** stored in logs.
- **Safe Demo Mode**:
  - Test all features immediately using built-in realistic sample files without installing Ollama or downloading models first.

---

## 📁 Project Structure

```text
d:\lazysort\
├── app.py                      # Main Streamlit web application
├── requirements.txt            # Python dependencies list
├── README.md                   # Complete beginner guide & documentation
├── core/                       # Core engine modules
│   ├── __init__.py
│   ├── extractor.py           # Text & metadata extraction (PDF, DOCX, TXT, Images)
│   ├── classifier.py          # Real Ollama AI classifier & transparent demo heuristics
│   ├── organizer.py           # Collision guard, safe move/copy, audit logging & undo
│   ├── ollama_client.py       # Ollama REST client, model check, health diagnostics
│   └── demo_data.py           # Generator for realistic sample test files
├── tests/                      # Automated unit & integration tests
│   ├── __init__.py
│   ├── test_extractor.py      # Tests extraction across PDF, DOCX, TXT, Images
│   ├── test_classifier.py     # Tests prompt generation, JSON parsing, vision flags
│   ├── test_organizer.py      # Tests collision avoidance, move/copy safety, undo
│   ├── test_ollama.py         # Tests connection errors, model discovery, diagnostics
│   └── test_integration.py   # Full end-to-end integration test
├── sample_files/              # Realistic demo files for safe testing
└── logs/                      # Audit logs (lazysort_audit.jsonl)
```

---

## 🚀 Beginner-Friendly Setup Instructions (Windows PowerShell)

Every step and command below is explained in plain, beginner-friendly language.

### Step 1: Open Windows PowerShell and Go to the Project Folder
Open **Windows PowerShell** from your Start menu, then enter:

```powershell
cd d:\lazysort
```

*What this does:* `cd` stands for "Change Directory". It moves your terminal into the LazySort project folder.

---

### Step 2: Create a Python Virtual Environment
Run:

```powershell
python -m venv .venv
```

*What this does:* A "virtual environment" creates an isolated sandbox for your Python packages. This prevents LazySort from interfering with other Python projects on your computer.

---

### Step 3: Activate the Virtual Environment
Run:

```powershell
.\.venv\Scripts\Activate.ps1
```

*What this does:* Activates your sandbox. You will see `(.venv)` appear at the beginning of your terminal prompt.

> **💡 PowerShell Note:** If Windows displays an error saying *`running scripts is disabled on this system`*, run this command once to allow the script for your current terminal session:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

---

### Step 4: Install Dependencies
Run:

```powershell
pip install -r requirements.txt
```

*What this does:* `pip` is Python's package manager. This reads `requirements.txt` and installs all necessary libraries (`streamlit`, `pypdf`, `python-docx`, `reportlab`, `requests`, `pytest`, etc.).

---

### Step 5: (Optional for Demo, Required for AI) Install Ollama
If you want to use the **real open-weight AI model**:

1. **Download Ollama**: Visit [https://ollama.com/download](https://ollama.com/download) and run the Windows installer.
2. **Start the Ollama Server**: Open a new PowerShell window and run:
   ```powershell
   ollama serve
   ```
   *(If Ollama is already running in your Windows taskbar system tray, you can skip this step!)*

3. **Download an Open-Weight Model**:
   In PowerShell, pull a lightweight, fast model:
   ```powershell
   # Recommended fast text model (~2 GB):
   ollama pull llama3.2

   # (Optional) Vision model for image and photo analysis (~4.7 GB):
   ollama pull llava
   ```

*What this does:* Downloads the open weights for the AI model directly to your machine so it runs 100% locally with zero internet dependency.

---

### Step 6: Run LazySort
From `d:\lazysort` (with your `.venv` activated), run:

```powershell
streamlit run app.py
```

*What this does:* Starts the local web server and automatically opens your web browser to **`http://localhost:8501`**.

---

## 🧪 How to Verify the Project Works

### Verification 1: Run the Automated Test Suite
Before opening the browser, verify that all backend modules pass their tests:

```powershell
python -m pytest -v
```

*Expected output:* You should see **24 passed** in green with zero failures.

---

### Verification 2: Test in Safe Demo Mode (No Ollama needed)
1. Open `http://localhost:8501` in your browser.
2. In the left sidebar, keep **🛡️ Safe Demo Mode** toggled ON.
3. Click the **"🧪 Demo & Sample Files"** tab.
4. Click **"📦 (Re)Generate Demo Files in sample_files/"**. You will see 8 sample files created (Invoice PDF, Resume DOCX, Lecture Notes TXT, Diagram PNG, etc.).
5. Switch to the **"📂 Organize Files"** tab.
6. Click **"🔍 Scan & Classify Files (Dry-Run Preview)"**.
7. Notice the results:
   - Metric cards show counts for Finance, Work, Education, Documents, Images, Others.
   - The interactive preview table shows proposed categories, destination paths, and reasons.
   - No files on your disk have been moved or touched yet!
8. Check the confirmation checkbox: *"✅ I have reviewed the preview above and explicitly authorize LazySort to organize these files."*
9. Click **"🚀 Confirm & Copy 8 Files"**.
10. Check the **"📜 History & Rollback"** tab to see the privacy-safe audit record and test the **"⏪ Undo Selected Batch"** button.

---

### Verification 3: Test Real Open-Weight AI via Ollama
1. Ensure Ollama is running (`ollama serve`) and you have pulled a model (`ollama pull llama3.2`).
2. Go to the **"🛠️ Diagnostics & Setup Guide"** tab:
   - Verify that **Ollama Service Status** shows a green checkmark `✅ Ollama service is running`.
   - In the **Quick AI Ping Test** section, click **"⚡ Test Model Ping"** to verify your local model responds with JSON.
3. In the left sidebar:
   - Turn **OFF** the **🛡️ Safe Demo Mode** toggle.
   - The header will turn to **⚡ REAL OLLAMA AI ACTIVE**.
   - Select your model (e.g. `llama3.2` or `llama3.2:latest`).
4. Go to the **"📂 Organize Files"** tab and click **"🔍 Scan & Classify Files (Dry-Run Preview)"**.
5. Observe the AI reasoning column: each file will display `[Ollama llama3.2]` followed by the model's actual semantic reasoning based on the extracted content!

---

## 🛡️ File Safety, Collisions & Privacy

| Feature | How LazySort Protects You |
| :--- | :--- |
| **No Unintended Changes** | Every operation requires a dry-run preview followed by explicit checkbox confirmation. |
| **Copy vs Move** | Copy mode is default. Originals remain untouched in their original folders. |
| **Collision Guard** | If `organized/Finance/invoice.pdf` exists, LazySort creates `invoice (1).pdf` instead of overwriting. |
| **1-Click Batch Undo** | Reverses moved files back to their source folders or deletes created copies. |
| **Privacy First** | Audit logs store only file paths, timestamps, sizes, and batch IDs. **Zero sensitive document text is logged.** |

---

## ❓ Common Troubleshooting Questions

### 1. PowerShell says: `Activate.ps1 cannot be loaded because running scripts is disabled`
- **Solution**: Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in PowerShell, then run `.\.venv\Scripts\Activate.ps1` again.

### 2. Streamlit says: `Ollama is currently unreachable`
- **Solution 1**: Toggle **Safe Demo Mode** in the sidebar to test without Ollama.
- **Solution 2**: Open PowerShell and run `ollama serve`. Make sure the URL in the sidebar is `http://localhost:11434`.

### 3. Model error: `Ollama model 'llama3.2' was not found`
- **Solution**: Open PowerShell and run `ollama pull llama3.2` to download the model weights.

### 4. How do I analyze image contents (receipts, whiteboards)?
- **Solution**: Text models like `llama3.2` cannot inspect image pixels. Download a vision model with `ollama pull llava` and select `llava` in the sidebar dropdown!
#   h o c t o b e r f e s t  
 #   h o c t o b e r f e s t  
 