You are a senior full-stack Python engineer and AI systems architect.

Build a complete Streamlit application for a multi-agent CSV transformation system.

The system receives multiple uploaded CSV files. One CSV must be selected as the primary CSV. The user interacts through a chat interface and gives natural-language transformation requests. The final output must always be executable Python code that takes the primary CSV and supporting CSVs as input, appends new columns to the primary CSV, and writes an enriched output CSV.

This is not a CSV chatbot. This is a CSV transformation code generator.

The system must never treat the final answer as a report, chart, or plain explanation. Every successful task must produce:

1. Generated transformation code.
2. Final enriched primary CSV.
3. Judge score out of 100.
4. Concise judge summary.
5. Agent trace.
6. Token usage per agent and total.
7. Time elapsed per agent and total.
8. Download button for final CSV and generated code.

Use Python, Streamlit, Polars, Pandas, requests, pydantic, and tiktoken.

Do not use Docker.
Do not use DuckDB.
Do not rely on external model downloads.
Do not require cloud infrastructure.
Do not assume CSVs can fit fully into LLM context.

The app must be clean, sleek, chat-based, and production-like.

============================================================
LOCAL LLM ENDPOINT REQUIREMENT
==============================

The system must make all LLM calls through this local endpoint:

http://localhost:5052/api/generate

Every request must be a POST request with JSON body:

{
"model": "gpt-5-mini",
"prompt": "<prompt text>"
}

The model value must always be:

gpt-5-mini

Do not make model configurable in the UI.
Do not use OpenAI SDK.
Do not use paid APIs.
Do not call any external LLM provider.
Do not use environment variables for the model unless also defaulting permanently to gpt-5-mini.

The response JSON will contain the LLM output inside the key:

response

Example response:

{
"response": "..."
}

The LLM client must extract:

response_json["response"]

If the response key is missing, fail gracefully and show a clear error in the UI.

Implement a centralized LLM client:

src/core/llm_client.py

It must expose:

class LocalLLMClient:
def **init**(self):
self.endpoint = "http://localhost:5052/api/generate"
self.model = "gpt-5-mini"

```
def generate(self, prompt: str) -> str:
    ...
```

Implementation requirements:

* Use requests.post.
* Send JSON exactly with keys model and prompt.
* Timeout should be configurable in code, default 180 seconds.
* Raise a clear exception if the endpoint is unavailable.
* Raise a clear exception if the response is not valid JSON.
* Raise a clear exception if the response key is missing.
* Return the string value of response_json["response"].
* Log prompt token estimate and response token estimate outside the client through the metrics system.

Example implementation behavior:

request_body = {
"model": "gpt-5-mini",
"prompt": prompt
}

res = requests.post(
"http://localhost:5052/api/generate",
json=request_body,
timeout=180
)

data = res.json()
llm_text = data["response"]

The app may include a MockLLM mode only as a developer fallback, but the default and primary behavior must use:

http://localhost:5052/api/generate

============================================================
CORE CONCEPT
============

The app must implement a multi-agent system that converts a user prompt into a safe, executable CSV enrichment script.

Input:

* Multiple CSVs uploaded by the user.
* One selected primary CSV.
* Natural-language prompt.

Output:

* Same rows as primary CSV.
* Same original columns as primary CSV.
* Additional generated columns.
* Saved enriched output CSV.

The generated transformation code must preserve the primary CSV row count unless the user explicitly requests filtering, but by default filtering is not allowed.

The code must append columns only. It must not delete or overwrite existing primary columns unless explicitly requested.

============================================================
WORKSPACE MODEL
===============

A workspace represents one chat session.

Every workspace must have its own directory:

workspaces/
workspace_<timestamp_or_uuid>/
input/
uploaded_csvs/
artifacts/
profile.json
task_spec.json
evidence_plan.json
operation_plan.json
generated_code.py
execution_log.txt
judge_input.json
judge_report.json
metrics.json
final_output.csv
transformation_summary.json
retries/
chat_history.json

Each workspace must be isolated at application level.

Because Docker is not available, implement a local sandbox by restricting all file operations to the workspace directory.

Generated code must run only inside the workspace.

Implement a safe execution wrapper:

* Run generated code in a subprocess.
* Set timeout.
* Capture stdout.
* Capture stderr.
* Pass only workspace file paths.
* Prevent writes outside the workspace by code convention and runtime checks.
* After execution, verify that expected output file exists inside workspace.
* Do not expose environment variables or secrets.
* Do not allow arbitrary shell commands from the LLM.
* The generated code should be a Python script, not shell code.

The executor should run:

python generated_code.py --primary <primary_path> --inputs_dir <inputs_dir> --output <output_path> --workspace <workspace_path>

============================================================
STREAMLIT UI REQUIREMENTS
=========================

Create a clean Streamlit app.

Layout:

Left sidebar:

* Upload multiple CSVs.
* Show uploaded files.
* Select primary CSV.
* Workspace selector or create new workspace button.
* Agent trace panel showing status of each agent:

  * Pending
  * Running
  * Completed
  * Failed
* Show current retry attempt if coding/execution loop is running.

Main area:

* Chat interface.
* User enters transformation prompt.
* Assistant shows live status.
* Final result card:

  * Judge score
  * Judge summary
  * New columns added
  * Output CSV download
  * Generated code download

Tabs:

1. Result
2. Generated Code
3. Judge Report
4. Metrics
5. Logs
6. Data Preview

Metrics tab must show:

* Token usage per agent.
* Total tokens.
* Time elapsed per agent.
* Total elapsed time.
* Number of coding attempts.
* Judge score per attempt if available.
* LLM endpoint used.
* LLM model used, always gpt-5-mini.

Data Preview tab:

* Show first 50 rows of final output CSV.
* Show original primary schema and final schema.
* Highlight newly added columns.

Failure behavior:

* If the system fails, show a clear user-friendly error.
* Do not crash the Streamlit app.
* If the coding agent fails 5 times, stop and show:
  “Unable to process this prompt at the moment. Please revise the request or inspect the logs.”
* Still show logs, metrics, and partial artifacts if available.

============================================================
AGENT SET
=========

Implement these agents as Python classes.

1. Task Understanding Agent
2. Data Profiler Agent
3. Evidence Requirement Agent
4. Evidence Builder Agent
5. Operation Planner Agent
6. Coding Agent
7. Execution Agent
8. Judge Agent
9. Repair Agent
10. User Explanation Agent

Each agent must:

* Have a clear input schema.
* Have a clear output schema.
* Save its output artifact to workspace.
* Track token usage using tiktoken.
* Track elapsed time.
* Update agent trace in the UI.
* Use LocalLLMClient for all LLM calls.
* Never call external APIs for LLM work.

============================================================
IMPORTANT: TIERED EVIDENCE REQUIREMENT
======================================

The system must not always build expensive evidence.

A prompt may contain many sub-problems. Each sub-problem may require a different level of evidence.

The Evidence Requirement Agent must split the user prompt into sub-tasks and assign an evidence tier to each.

Evidence tiers:

Tier 0: Schema-only
Use when the task can be solved using only column names and data types.

Examples:

* Add rounded amount column.
* Create withdrawal bucket.
* Convert date format.
* Calculate simple difference between two columns.

Needed evidence:

* Schema
* Data types

Tier 1: Profile-level
Use when the task needs column statistics.

Examples:

* Create risk score from amount and frequency.
* Add percentile rank.
* Add amount band based on distribution.

Needed evidence:

* Schema
* Null percentage
* Min/max
* Mean/median where applicable
* Unique counts

Tier 2: Sample-based
Use when the task needs semantic inference about columns.

Examples:

* Find which column contains customer name.
* Infer which column is line-item description.
* Understand meaning of coded columns.

Needed evidence:

* Schema
* Profile
* Small representative sample

Tier 3: Unique-value evidence
Use when row-wise semantic classification can be compressed by classifying unique values.

Examples:

* Identify administrative line items.
* Categorize expense descriptions.
* Flag legal/accounting/HR/software/office items.

Needed evidence:

* Unique values from target text columns
* Frequency
* Optional sample context columns

Strategy:

* Do not classify every row.
* Extract unique values.
* Classify unique values in LLM batches.
* Map classification results back to the primary CSV.

Tier 4: Contextual evidence
Use when one text value is insufficient and surrounding columns are needed.

Examples:

* Classify line items based on description + department + account type.
* Identify suspicious transactions using amount, terminal, time, and transaction type.

Needed evidence:

* Target column
* Context columns
* Group statistics
* Representative examples

Tier 5: Dataset-wide reasoning
Use for relational, duplicate, anomaly, or pattern tasks.

Examples:

* Identify duplicate vendors.
* Find entity matches.
* Detect unusual behavior.
* Create fraud/anomaly scores.

Needed evidence:

* Candidate groups
* Aggregations
* Similarity features
* Cross-row statistics

The Evidence Requirement Agent output must look like:

{
"subtasks": [
{
"subtask_id": "S1",
"description": "...",
"evidence_tier": 0,
"required_columns": [],
"reason": "..."
},
{
"subtask_id": "S2",
"description": "...",
"evidence_tier": 3,
"required_columns": ["line_item_description"],
"reason": "Semantic classification of unique descriptions is required."
}
]
}

The Evidence Builder should only build evidence required by the assigned tiers.

============================================================
DATA PROFILING
==============

Data Profiler Agent must inspect uploaded CSVs using Polars where possible.

For each CSV, create profile.json:

{
"files": [
{
"file_name": "...",
"path": "...",
"row_count_estimate": 0,
"columns": [
{
"name": "...",
"dtype": "...",
"null_count": 0,
"null_percent": 0.0,
"unique_count_estimate": 0,
"sample_values": [],
"min": null,
"max": null
}
],
"sample_rows": []
}
],
"primary_csv": "..."
}

For large CSVs:

* Avoid loading all rows into pandas.
* Prefer Polars scan_csv/read_csv.
* Use limited rows for samples.
* Compute profiles carefully.
* Fail gracefully if a column cannot be profiled.

============================================================
TASK UNDERSTANDING AGENT
========================

Task Understanding Agent converts user prompt into a structured task.

It must call the local LLM endpoint through LocalLLMClient.

Prompt requirements for this agent:

* Include user prompt.
* Include primary CSV name.
* Include file/profile summary.
* Ask for strict JSON.
* Do not ask the LLM to inspect full CSV data.
* Force the output to describe column-generating transformations only.

It must identify:

* Primary CSV transformation goal.
* Supporting CSVs needed.
* Expected new columns.
* Whether multiple subtasks exist.
* Whether semantic classification is needed.
* Whether aggregation/windowing/joining is needed.
* Whether output must include confidence/reason columns.

Output:

{
"user_prompt": "...",
"primary_csv": "...",
"overall_goal": "...",
"subtasks": [],
"expected_new_columns": [],
"constraints": [
"preserve primary rows",
"preserve original columns",
"append new columns only"
]
}

============================================================
EVIDENCE REQUIREMENT AGENT
==========================

Evidence Requirement Agent must call the local LLM endpoint through LocalLLMClient.

It determines minimum evidence needed per subtask.

It must not always request evidence.

It must choose the lowest sufficient evidence tier.

It must handle prompts that contain many requirements where each requirement may need a different evidence level.

Output:

{
"subtasks": [
{
"subtask_id": "S1",
"description": "...",
"evidence_tier": 0,
"required_columns": [],
"context_columns": [],
"requires_llm_classification": false,
"reason": "..."
}
]
}

============================================================
EVIDENCE BUILDER AGENT
======================

Evidence Builder Agent may use Polars/Pandas and may call the local LLM endpoint only when semantic classification mappings are needed.

It builds only required evidence.

For Tier 0:

* No evidence file beyond schema/profile.

For Tier 1:

* Use profile statistics.

For Tier 2:

* Create sample evidence JSON.

For Tier 3:

* Extract unique target values.
* Include frequency.
* Include optional sample context.
* If classification is required, call LocalLLMClient in batches.
* Save classification mapping CSV/JSON.

For Tier 4:

* Build contextual unique evidence using target + context columns.
* Batch classify or summarize as needed.

For Tier 5:

* Build candidate groups, aggregations, similarity features, or anomaly candidate evidence.

For LLM classification batches:

* Use endpoint http://localhost:5052/api/generate.
* Always send model gpt-5-mini.
* Extract response key.
* Ask for strict JSON array.
* Save raw LLM responses for debugging.
* Recover gracefully from malformed JSON where possible.
* Do not send entire CSV rows unless necessary.
* Use compact IDs and map back later.

============================================================
OPERATION PLANNER AGENT
=======================

Operation Planner Agent creates a concrete implementation plan.

It must call the local LLM endpoint through LocalLLMClient.

It must classify each subtask as one or more of:

* direct_column_creation
* row_wise_semantic_classification
* multi_csv_lookup_join
* aggregation_feature
* date_window_feature
* text_normalization
* rule_extraction
* scoring
* anomaly_detection
* duplicate_detection
* entity_resolution
* exploratory_to_column_generation

Important:
Even if the user asks for insights, the planner must convert insights into columns to add to the primary CSV.

Example:
User asks:
“Find suspicious transactions.”

Planner should produce columns:

* suspicious_transaction_score
* suspicious_transaction_flag
* suspicious_transaction_reason

The Operation Planner output must include:

* Columns to add.
* Column types.
* Logic for each column.
* Evidence needed.
* Whether LLM classification is required.
* Whether batch classification files are needed.
* Join keys if supporting CSVs are required.
* Failure risks.

============================================================
SEMANTIC CLASSIFICATION DESIGN
==============================

For prompts like:
“Identify administrative line items”

The system should not send all rows to the LLM.

It should:

1. Detect target text column.
2. Extract unique values.
3. Include frequency.
4. Include context columns if needed.
5. Batch classify using LocalLLMClient.
6. Save classification mapping.
7. Generated code maps classification back to primary rows.

The generated columns should not only be boolean.

For classification tasks, add audit columns:

* <task>*flag or is*<task>
* <task>_category
* <task>_confidence
* <task>_reason

Example:

* is_administrative_line_item
* administrative_category
* administrative_confidence
* administrative_reason

============================================================
CODING AGENT
============

Coding Agent must call the local LLM endpoint through LocalLLMClient.

Coding Agent must generate a complete Python script.

The script must:

* Use argparse.
* Accept:
  --primary
  --inputs_dir
  --output
  --workspace
* Use Polars preferably.
* Use Pandas only when easier and safe.
* Read the primary CSV.
* Read supporting CSVs if needed.
* Add new columns.
* Preserve all primary rows.
* Preserve original columns.
* Save final output CSV.
* Save a small transformation_summary.json.
* Avoid hardcoded absolute paths.
* Avoid internet calls.
* Avoid LLM calls inside generated transformation code unless explicitly needed and already planned.
* Prefer using prebuilt evidence/classification mapping artifacts instead of calling LLM from generated code.
* Avoid deleting files.
* Avoid shell commands.
* Avoid writing outside workspace.
* Handle missing columns gracefully with clear errors.

Generated script must include:

def transform(primary_path, inputs_dir, output_path, workspace_path):
...

if **name** == "**main**":
...

The script must be self-contained.

If LLM classification mappings are already created as artifacts, the generated code should read them from workspace and map them back.

Coding Agent prompt must include:

* User prompt.
* Task spec.
* Evidence requirement plan.
* Operation plan.
* Profile summary.
* Available evidence artifact paths.
* Workspace artifact paths.
* Primary CSV path variable.
* Inputs directory variable.
* Required output path variable.
* Previous failure feedback if any.
* Judge weaknesses if retrying due to low score.

Coding Agent must return only code or a JSON object with code field. The app must robustly extract the code and save it as generated_code.py.

============================================================
EXECUTION AND REPAIR LOOP
=========================

The Coding Agent must be looped.

Maximum attempts: 5.

Loop:

1. Generate code.
2. Run code guard.
3. Execute code.
4. If execution succeeds, send to Judge Agent.
5. If execution fails, send error logs to Repair Agent.
6. Repair Agent updates code.
7. Retry.

If 5 attempts fail:

* Stop.
* Mark status failed.
* Show graceful failure message.
* Save all logs.
* Do not continue to judge as successful.

Repair Agent must call the local LLM endpoint through LocalLLMClient.

Repair Agent input:

* User prompt
* Task spec
* Operation plan
* Evidence requirement plan
* Generated code
* Error traceback
* Execution logs
* Data profile
* Previous attempt number
* Workspace paths

Repair Agent output:

* Corrected generated_code.py
* Explanation of fix

============================================================
JUDGE AGENT
===========

Use a full LLM judge with detailed rubric.

Do not implement a separate validation agent.

Judge Agent must call the local LLM endpoint through LocalLLMClient.

The Judge Agent receives:

* User prompt
* Task spec
* Evidence requirement plan
* Operation plan
* Generated code
* Execution log
* Profile
* Output schema
* Input/output row counts
* Sample of final output
* List of added columns
* Any classification mapping sample
* Any warnings

The judge must score out of 100.

Rubric:

1. Requirement understanding: 20 points
   Did the system correctly understand the user’s transformation request?

2. Output column correctness: 20 points
   Were the correct columns added to the primary CSV?

3. Transformation logic correctness: 20 points
   Does the code logic match the requested transformation?

4. Coverage and edge cases: 15 points
   Does it handle all rows, nulls, duplicates, missing matches, and ambiguous cases?

5. Semantic reasoning quality: 10 points
   For classification tasks, are the classifications, categories, confidence values, and reasons reasonable?

6. Code quality and scalability: 10 points
   Is the code safe, readable, scalable, and suitable for large CSVs?

7. User-facing clarity: 5 points
   Is the result easy to understand?

Judge output schema:

{
"score": 0,
"passed": true,
"confidence_label": "Low | Medium | High",
"summary": "One concise paragraph",
"strengths": [],
"weaknesses": [],
"required_fixes": [],
"recommended_review_rows": [],
"columns_added": [],
"retry_recommended": false
}

Threshold:

* Default passing threshold: 75.
* If score < 75, retry with renewed knowledge.
* Retry should use judge weaknesses and required fixes.
* Maximum total code attempts remains 5.
* If score remains below threshold after retries are exhausted, show graceful failure.

Important:
The judge summary must be concise. Show it in the UI result card.

============================================================
TOKEN COUNTING
==============

Use tiktoken to estimate token usage per agent.

Implement utility:

count_tokens(text, model_name="gpt-5-mini")

Because tiktoken may not recognize gpt-5-mini, implement safe fallback:

try:
encoding = tiktoken.encoding_for_model("gpt-5-mini")
except Exception:
encoding = tiktoken.get_encoding("cl100k_base")

Track:

* prompt_tokens
* completion_tokens
* total_tokens
* elapsed_seconds

For non-LLM agents, token count can be 0, but elapsed time must still be tracked.

Save metrics.json:

{
"llm": {
"endpoint": "http://localhost:5052/api/generate",
"model": "gpt-5-mini",
"response_key": "response"
},
"agents": {
"task_understanding": {
"prompt_tokens": 0,
"completion_tokens": 0,
"total_tokens": 0,
"elapsed_seconds": 0.0
}
},
"total_tokens": 0,
"total_elapsed_seconds": 0.0,
"attempts": 0
}

Display this in Metrics tab.

============================================================
LOCAL LLM CLIENT IMPLEMENTATION DETAILS
=======================================

Implement this file:

src/core/llm_client.py

It should contain:

import requests

class LocalLLMError(Exception):
pass

class LocalLLMClient:
def **init**(self, timeout: int = 180):
self.endpoint = "http://localhost:5052/api/generate"
self.model = "gpt-5-mini"
self.timeout = timeout

```
def generate(self, prompt: str) -> str:
    payload = {
        "model": self.model,
        "prompt": prompt
    }

    try:
        response = requests.post(
            self.endpoint,
            json=payload,
            timeout=self.timeout
        )
    except requests.RequestException as exc:
        raise LocalLLMError(
            f"Local LLM endpoint unavailable: {self.endpoint}. Error: {exc}"
        ) from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise LocalLLMError(
            f"Local LLM endpoint returned HTTP {response.status_code}: {response.text[:1000]}"
        )

    try:
        data = response.json()
    except Exception as exc:
        raise LocalLLMError(
            f"Local LLM endpoint did not return valid JSON. Raw response: {response.text[:1000]}"
        ) from exc

    if "response" not in data:
        raise LocalLLMError(
            f"Local LLM response missing required key 'response'. Available keys: {list(data.keys())}"
        )

    result = data["response"]

    if result is None:
        raise LocalLLMError("Local LLM response key 'response' was null.")

    return str(result)
```

All agents must use this client.
No agent should directly call requests.post except this client.

============================================================
STATUS AND AGENT TRACE
======================

The UI must clearly show status.

Trace example:

Task Understanding Agent: Completed
Data Profiler Agent: Completed
Evidence Requirement Agent: Completed
Evidence Builder Agent: Completed
Operation Planner Agent: Completed
Coding Agent Attempt 1: Failed
Repair Agent Attempt 1: Completed
Coding Agent Attempt 2: Completed
Execution Agent: Completed
Judge Agent: Score 83

Agent trace must be visible in sidebar and updated as each agent completes.

============================================================
DATAFRAME HANDLING
==================

Use Polars for large data.

Rules:

* Prefer pl.scan_csv for lazy operations.
* Use pl.read_csv when needed.
* For preview, read only first 50 rows.
* Avoid converting full large CSV to pandas.
* Pandas may be used for small mapping files or small samples.

For classification mapping:

* Use unique values extracted with Polars.
* Save mapping CSV.
* Join/map back using Polars.

============================================================
SECURITY AND SAFETY WITHOUT DOCKER
==================================

Since Docker is not available, implement practical local safeguards:

* Generated code runs in subprocess.
* Working directory is workspace.
* Input files are copied into workspace/input.
* Output must be workspace/artifacts/final_output.csv.
* Reject generated code if it contains suspicious patterns:

  * os.remove
  * os.unlink
  * shutil.rmtree
  * subprocess
  * socket
  * requests.get
  * requests.post except in src/core/llm_client.py
  * urllib
  * http://
  * https://
  * open('/etc
  * open('C:\
  * pathlib.Path.home
  * os.environ
  * dotenv
  * eval(
  * exec(
  * **import**
* This is not perfect sandboxing, but it is acceptable for local controlled usage.
* Clearly comment in code that this is a restricted local execution wrapper, not a hardened security sandbox.

Important:
Generated transformation scripts should not directly call the LLM endpoint unless explicitly required by the operation plan. The preferred design is:

* Agents call the LLM.
* Evidence/classification artifacts are saved.
* Generated code reads artifacts and transforms the CSV.

============================================================
PROJECT STRUCTURE
=================

Create this structure:

csv_transform_agent_app/
app.py
requirements.txt
README.md
src/
agents/
base.py
task_understanding.py
data_profiler.py
evidence_requirement.py
evidence_builder.py
operation_planner.py
coding_agent.py
repair_agent.py
execution_agent.py
judge_agent.py
user_explanation.py
core/
workspace.py
llm_client.py
metrics.py
token_counter.py
safe_executor.py
code_guard.py
schemas.py
csv_utils.py
ui/
components.py
styles.py
workspaces/
.gitkeep

============================================================
REQUIREMENTS
============

requirements.txt should include:

streamlit
polars
pandas
tiktoken
pydantic
requests
python-dotenv

Do not include duckdb.
Do not include docker libraries.
Do not include OpenAI SDK.

============================================================
README
======

README must explain:

* What the system does.
* How to run it.
* The local LLM endpoint requirement:
  http://localhost:5052/api/generate
* The request format:
  {"model": "gpt-5-mini", "prompt": "..."}
* The response format:
  {"response": "..."}
* How to upload CSVs.
* How to select primary CSV.
* How workspaces work.
* What the judge score means.
* Limitations of local subprocess sandboxing without Docker.

============================================================
IMPLEMENTATION QUALITY
======================

Build the actual working code.

Do not only create placeholders.

Where LLM behavior is needed, create strong prompts inside each agent.

Every agent prompt must be explicit and must request JSON output when structured output is needed.

Implement robust JSON extraction from LLM responses.

If JSON parse fails:

* Try to extract JSON block.
* If still fails, save raw response.
* Fail gracefully with a clear message.

The local LLM endpoint may sometimes return malformed JSON content inside response. The app must handle this gracefully.

============================================================
FINAL ACCEPTANCE CRITERIA
=========================

The app is accepted only if:

1. Streamlit app starts successfully.
2. User can upload multiple CSVs.
3. User can select primary CSV.
4. User can enter a prompt in chat.
5. A workspace is created.
6. Agents run in sequence.
7. All LLM agents use http://localhost:5052/api/generate.
8. All LLM requests use model gpt-5-mini.
9. All LLM responses are read from the response key.
10. Agent trace is shown.
11. Code is generated.
12. Code is executed in workspace-specific local restricted executor.
13. Failed code is repaired up to 5 attempts.
14. If all attempts fail, the app fails gracefully.
15. If successful, final_output.csv is created.
16. Original primary columns are preserved.
17. Primary row count is preserved by default.
18. New columns are appended.
19. Judge Agent scores output out of 100.
20. If judge score < 75, retry with renewed knowledge until max attempts.
21. Metrics tab shows token usage per agent and total.
22. Metrics tab shows elapsed time per agent and total.
23. Metrics tab shows LLM endpoint and model.
24. Judge summary is displayed clearly.
25. Generated code and final CSV are downloadable.
26. Logs are visible.
27. Data preview works.
28. No DuckDB.
29. No Docker.
30. No OpenAI SDK.
31. Polars is preferred.
32. Pandas is used only where safe.

Build this as a complete, usable application.
