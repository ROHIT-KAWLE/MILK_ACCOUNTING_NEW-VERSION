# 🥛 Milk Accounting Pro (दुग्ध व्यवसाय हिशोब प्रणाली)

An enterprise-grade milk distribution, daily delivery ledger, and accounting system built with Streamlit, Supabase, and Python.

---

## 🚀 Features

- **📱 Phone Lock Screen Gate**: Secured with a mobile-style 3×4 numeric keypad. Automatically unlocks upon typing **`7744`** with zero page reloads, haptic vibration, and anti-brute-force lockout.
- **📋 Daily Dispatch Matrix**: Ultra-fast daily entry grid with non-sortable, locked column headers to prevent accidental sorting during rapid non-tech operator data entry.
- **🧾 Credit / Cash Memo Billing**: Clean, professional A4-printable bills with Opening Balance, Current Period Sales, Less Payments, and Net Amount Payable. Includes optional FAT / SNF column toggles and auto currency-to-words conversion in Indian Rupees.
- **👥 Staff Attendance & Date-Effective Wage Revision**: Full Day (1.0), Half Day (0.5), and Absent (0.0) tracking with date-effective wage adjustments that only apply from the revision date onward without altering historical pay.
- **🚚 Driver Counter Handover Reconciliation**: Route-based daily cash collection vs operational expenses (fuel, bhatta, vehicle maintenance) vs counter cash handovers.
- **🛡️ Multi-Sheet Excel & ZIP Backups**: Download comprehensive 5-sheet `.xlsx` workbooks (Daily Ledger, Worker Attendance & Wages, Driver Cash Handovers, Route Expenses, Staff Directory) and full `.zip` database archives for any date range.
- **🎙️ Marathi AI Voice Assistant**: Natural Marathi speech-to-text parser for hands-free milk entry recording.

---

## ☁️ Deployment on Streamlit Community Cloud

Deploying Milk Accounting Pro to Streamlit Cloud takes under 2 minutes:

### Step 1: Push Repository to GitHub
Ensure all code and components are pushed to your GitHub repository:
```bash
git init
git add .
git commit -m "feat: production-ready Milk Accounting Pro"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### Step 2: Connect with Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
2. Click **New app**.
3. Choose your repository, branch (`main`), and set **Main file path** to:
   ```text
   app.py
   ```
4. Click **Advanced settings...** and navigate to **Secrets**.

### Step 3: Configure Supabase Secrets
Paste your Supabase credentials into the Secrets box:
```toml
[supabase]
url = "https://your-project.supabase.co"
service_role_key = "your-service-role-key"
anon_key = "your-anon-key"
```
*(Reference: see `.streamlit/secrets.toml.example`)*

5. Click **Deploy!**

---

## 🔒 Security & Access Control

- **Default PIN**: `7744`
- **Dial Pad**: 3×4 numeric grid (touch/click or physical keyboard 0-9).
- **Auto-Unlock**: Immediate evaluation on the 4th digit.
- **Security Features**:
  - Constant-time verification (`hmac.compare_digest`)
  - 5-attempt rate-limiting with 30s lockout
  - Zero URL parameter exposure
  - OS-validated SSL/TLS root certificate validation

---

## 💻 Local Development Setup

### 1. Prerequisites
- Python 3.12 (as specified in `runtime.txt`)
- Virtual environment (recommended)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd milk_account-main

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Local Secrets Setup
Create `.streamlit/secrets.toml`:
```toml
[supabase]
url = "https://your-project.supabase.co"
service_role_key = "your-service-role-key"
anon_key = "your-anon-key"
```

### 4. Run Application
```bash
streamlit run app.py
```

### 5. Run Automated Tests
```bash
python -m pytest tests/ -v
```

---

## 📁 Repository Structure

```text
├── .github/workflows/ci.yml       # GitHub Actions automated CI test suite
├── .streamlit/
│   ├── config.toml                # Light theme & headless server config
│   └── secrets.toml.example       # Secrets template for Streamlit Cloud
├── ai/                            # Marathi voice transcription & AI parsing
├── components/
│   └── phone_lock/
│       └── index.html             # Phone dial pad component (auto-unlock, PIN 7744)
├── data/                          # Staff attendance, wage revision & local tables
├── invoices/                      # Generated printable customer bills directory
├── tests/                         # 67 automated unit and integration tests
├── ai_engine.py                   # Natural language intent classifier & tokenizer
├── app.py                         # Main Streamlit enterprise accounting application
├── pyproject.toml                 # Ruff linter and Pytest configuration
├── requirements.txt               # Pinned Python package dependencies
└── runtime.txt                    # Python 3.12 runtime declaration
```

---

## 🧪 Quality & Compliance

- **Test Suite**: 67 automated tests passing 100% across all accounting, billing, attendance, wage revision, and security modules.
- **Linting**: 100% clean with Ruff (`python -m ruff check .`).
- **Compilation**: Verified bytecode compilation (`python -m compileall app.py`).
