# Loan Risk MAS — Setup & Run Guide
### Automated Loan Applicant Risk Assessment Multi-Agent System
**SE4010 CTSE Assignment 2 | LangGraph + Ollama | Zero Cloud Cost**

---

## What This System Does

A four-agent pipeline that reads a JSON loan application, validates it,
computes financial risk (DTI, LTV), checks a local fraud database,
and outputs a professional HTML decision report — fully locally, no paid APIs.

```
[JSON File] → Agent1 Validate → Agent2 Financial → Agent3 Fraud → Agent4 Report
                                                                        ↓
                                                              data/reports/*.html
```

---

## System Requirements

| Requirement | Minimum |
|---|---|
| OS | Windows 11 (64-bit) |
| Python | 3.11 or 3.12 |
| RAM | 4 GB free (8 GB recommended) |
| Disk | 5 GB free (for model) |
| Ollama | Installed and running |

---

## Part 1 — Ollama Setup

### Step 1: Install Ollama
1. Go to **https://ollama.com**
2. Click **Download for Windows**
3. Run the installer — it adds `ollama` to your PATH automatically

### Step 2: Pull the recommended model

Open **Command Prompt** or **PowerShell** and run:

```bash
ollama pull llama3.2
```

> This downloads ~2 GB once. You only need to do this once.

**If your PC has less than 4 GB free RAM**, use the smaller model instead:
```bash
ollama pull phi3:mini
```
Then open `config.py` and change:
```python
OLLAMA_MODEL = "phi3:mini"
```

### Step 3: Verify Ollama is working
```bash
ollama run llama3.2
```
Type `hello` and press Enter. You should get a response.
Press `Ctrl + D` to exit.

> **Important:** Ollama must be running in the background when you run the project.
> You can start it from the system tray or by running `ollama serve` in a terminal.

---

## Part 2 — Project Setup

### Step 1: Open the project in VS Code

1. Extract the `loan_risk_mas` folder anywhere (e.g. `C:\Projects\loan_risk_mas`)
2. Open VS Code
3. **File → Open Folder** → select `loan_risk_mas`

### Step 2: Open the VS Code terminal

Press **Ctrl + ` ** (backtick) to open the integrated terminal.

### Step 3: Create a Python virtual environment

```bash
python -m venv venv
```

### Step 4: Activate the virtual environment

```bash
venv\Scripts\activate
```

You should see `(venv)` appear at the start of your prompt.

> **If you get an execution policy error**, run this first:
> ```bash
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then try activating again.

### Step 5: Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `langgraph` — multi-agent orchestration framework
- `langchain-core` — base LangChain components
- `langchain-ollama` — connects agents to your local Ollama model
- `pytest` — test runner

> Installation takes 1–3 minutes. You will see packages downloading.

---

## Part 3 — First-Time Initialization

### Step 6: Set up the fraud database

This creates the SQLite database that Agent 3 queries.
**Run this only once:**

```bash
python db_setup.py
```

Expected output:
```
[OK] Fraud database ready at: data/fraud_patterns.db
```

---

## Part 4 — Running the System

### Run with the sample application (normal applicant)

```bash
python main.py
```

This processes `data/sample_application.json` (Priya Fernando).

### Run with the high-risk application

```bash
python main.py data/sample_application_highrisk.json
```

This processes a high-risk applicant with fraud flags.

### Run with the invalid application

```bash
python main.py data/sample_application_invalid.json
```

This shows how Agent 1 catches bad data and halts the pipeline.

---

## Part 5 — Expected Output

### Terminal output (during run)
```
2024-01-15 10:23:41 | INFO     | LoanRiskMAS | ╔══════════════...
2024-01-15 10:23:41 | INFO     | LoanRiskMAS | AGENT 1 — Application Validator: starting
2024-01-15 10:23:41 | INFO     | LoanRiskMAS |   Input: application_path = data/sample_application.json
2024-01-15 10:23:44 | INFO     | LoanRiskMAS |   LLM summary: The application data for Priya Fernando...
2024-01-15 10:23:44 | INFO     | LoanRiskMAS | AGENT 2 — Financial Risk Analyzer: starting
2024-01-15 10:23:44 | INFO     | LoanRiskMAS |   DTI=37.5%  LTV=66.7%  Score=38.2  Tier=MEDIUM
...

════════════════════════════════════════════════════════════
  LOAN RISK ASSESSMENT — COMPLETE
════════════════════════════════════════════════════════════
  Applicant  : Priya Fernando
  Loan Amount: 8,000,000
  Fin. Score : 38.2/100  (MEDIUM)
  Fraud Score: 0.0/100  (LOW)
  Fraud Flags: 0
  DECISION   : APPROVE
  Report     : C:\Projects\loan_risk_mas\data\reports\loan_report_...html
════════════════════════════════════════════════════════════
```

### HTML Report
Open the file path shown in the terminal output.
The report includes:
- Applicant summary table
- Financial metrics (DTI, LTV, scores)
- Fraud flag list
- Colour-coded decision banner (green/amber/red)
- LLM-generated decision reasoning

### Log File
Full execution trace is saved to `logs/agent_run.log`.
Open it in VS Code to see every agent's input and output.

---

## Part 6 — Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run one student's tests only
```bash
pytest tests/test_agent1.py -v    # Student 1
pytest tests/test_agent2.py -v    # Student 2
pytest tests/test_agent3.py -v    # Student 3
pytest tests/test_agent4.py -v    # Student 4
```

### Expected test output
```
tests/test_agent1.py::TestTool1ValidApplication::test_valid_application_passes PASSED
tests/test_agent1.py::TestTool1ValidApplication::test_valid_application_returns_data PASSED
...
========================= 35 passed in 1.23s =========================
```

> Tests do NOT require Ollama to be running — they test the Python
> tools directly, not the LLM calls.

---

## Part 7 — Project Structure

```
loan_risk_mas/
│
├── config.py                    ← Change OLLAMA_MODEL here
├── state.py                     ← Shared state (Student 1 writes)
├── logger_config.py             ← Logging setup (Student 1 writes)
├── db_setup.py                  ← Creates fraud DB (Student 1 writes, run once)
├── main.py                      ← LangGraph orchestration (Student 1 writes)
│
├── agents/
│   ├── agent1_validator.py      ← Student 1
│   ├── agent2_financial_analyzer.py  ← Student 2
│   ├── agent3_fraud_detector.py ← Student 3
│   └── agent4_decision_writer.py ← Student 4
│
├── tools/
│   ├── tool1_json_validator.py  ← Student 1
│   ├── tool2_financial_calc.py  ← Student 2
│   ├── tool3_fraud_db_query.py  ← Student 3
│   └── tool4_report_writer.py   ← Student 4
│
├── tests/
│   ├── test_agent1.py           ← Student 1
│   ├── test_agent2.py           ← Student 2
│   ├── test_agent3.py           ← Student 3
│   └── test_agent4.py           ← Student 4
│
├── data/
│   ├── sample_application.json            ← Normal applicant
│   ├── sample_application_highrisk.json   ← High-risk applicant
│   ├── sample_application_invalid.json    ← Bad data (testing Agent 1)
│   ├── fraud_patterns.db                  ← Created by db_setup.py
│   └── reports/                           ← HTML reports saved here
│
├── logs/
│   └── agent_run.log                      ← Full execution trace
│
└── requirements.txt
```

---

## Part 8 — Troubleshooting

### "Connection refused" or "LLM call failed"
Ollama is not running. Open a new terminal and run:
```bash
ollama serve
```
Leave that terminal open and run `main.py` in a different terminal.

### "model 'llama3.2' not found"
You need to pull the model first:
```bash
ollama pull llama3.2
```

### Agents complete but LLM responses are rule-based
This is normal and expected — the code has graceful fallbacks.
The system works correctly without LLM responses because all
decisions are made by Python code (the tools). The LLM only
adds human-readable text explanations.

### "venv\Scripts\activate is not recognized"
Use this instead:
```bash
.\venv\Scripts\Activate.ps1
```

### pytest: "ModuleNotFoundError"
Make sure your virtual environment is activated (you see `(venv)`)
and run pytest from the project root directory:
```bash
cd C:\Projects\loan_risk_mas
pytest tests/ -v
```

### Slow LLM responses
Small models on CPU can take 30–60 seconds per agent.
This is normal. Switch to `phi3:mini` in `config.py` for faster responses.

---

## Part 9 — What Meets Each Rubric Criterion

| Criterion | How this project satisfies it |
|---|---|
| **Multi-Agent Orchestration (15%)** | LangGraph StateGraph with 4 nodes; conditional routing after Agent 1 |
| **Tool Usage (10%)** | 4 custom tools: JSON validator, financial calculator, SQLite query, HTML writer |
| **State Management (10%)** | TypedDict `LoanState` passed through all nodes; every field documented |
| **Observability (part of 10%)** | `logs/agent_run.log` records every agent input, tool call, and output |
| **Individual Agent Design (20%)** | Each agent has a unique system prompt, persona, and output contract |
| **Individual Custom Tool (20%)** | Each tool has full type hints, Args/Returns/Raises docstrings, error handling |
| **Testing (10%)** | 35+ pytest tests across all 4 agents; edge cases and error paths covered |

---

## Part 10 — Demo Video Guide (4–5 minutes)

Suggested recording order:

1. **(0:00)** Show `config.py` — explain the model choice
2. **(0:20)** Show the folder structure briefly
3. **(0:45)** Run `python db_setup.py` — show database created
4. **(1:00)** Run `python main.py` — show all 4 agents running live
5. **(2:00)** Open the HTML report in browser — walk through sections
6. **(2:45)** Run `python main.py data/sample_application_highrisk.json` — show REJECT
7. **(3:15)** Open `logs/agent_run.log` in VS Code — show full trace
8. **(3:45)** Run `pytest tests/ -v` — show all tests passing
9. **(4:20)** Briefly show one tool file (type hints, docstring) and one agent file

Use **OBS Studio** (free) or Windows **Xbox Game Bar** (Win + G) to record.

---

*Loan Risk MAS — SE4010 CTSE Assignment 2*
