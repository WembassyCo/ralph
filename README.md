# Ralph

![Ralph](ralph.webp)

Ralph is an autonomous AI agent loop that runs [Amp](https://ampcode.com), Claude API, or Ollama repeatedly until all PRD items are complete. Each iteration is a fresh LLM instance with clean context. Memory persists via git history, `progress.txt`, and `prd.json`.

Based on [Geoffrey Huntley's Ralph pattern](https://ghuntley.com/ralph/).

[Read Ryan Carson's article on how he uses Ralph](https://x.com/ryancarson/status/2008548371712135632)

[Read how I updated Ralph to leverage Ollama](https://medium.com/@cmcintosh_3425/keep-ralph-from-eating-all-of-your-tokens-bac5dfe4cb97)

## Prerequisites

- **Python 3.11+** installed
- **One of the following LLM options:**
  - [Ollama](https://ollama.ai/) running locally (recommended for cost-free operation)
  - [Claude API](https://www.anthropic.com/api) key (via `ANTHROPIC_API_KEY` environment variable)
  - [Amp CLI](https://ampcode.com) installed and authenticated
- **Git repository** for your project
- **Optional:** [Edna](https://github.com/wembassyco/edna) for easy PRD creation and execution

## Setup

### Install Python Dependencies

```bash
cd ralph
pip install -r requirements.txt
```

### Configure LLM Provider

Ralph auto-detects available LLM providers in this order:
1. **Ollama** (checks for running instance at `http://localhost:11434`)
2. **Claude API** (checks for `ANTHROPIC_API_KEY` environment variable)
3. **Amp CLI** (checks for `amp` command in PATH)

You can override auto-detection using a `config.json` file or command-line flag:

```json
{
  "llm": {
    "provider": "claude",
    "model": "claude-3-5-sonnet-20241022",
    "apiKey": "sk-ant-...",
    "ollamaUrl": "http://localhost:11434"
  }
}
```

Or use the `--config` flag:
```bash
python ralph.py 10 --config my-config.json
```

### Set up Environment Variables (Optional)

For Claude API:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

For custom Ollama URL:
```bash
export OLLAMA_URL="http://localhost:11434"
```

## Workflow

### Recommended: Use Edna (Easiest)

**[Edna](https://github.com/wembassyco/edna)** is a web UI that makes it easy to create PRDs and run Ralph with real-time progress tracking.

1. **Start Edna:**
   ```bash
   docker-compose up
   ```
   Visit [http://localhost:5173](http://localhost:5173)

2. **Create a PRD:**
   - Click "New PRD"
   - Chat with Edna to plan your feature
   - Edna will generate user stories with acceptance criteria

3. **Run Ralph:**
   - Click "▶ Run Ralph" button
   - Configure iterations, LLM provider, and model
   - Watch real-time progress with live logs
   - Optional: Connect to GitHub for automatic commits

That's it! Edna handles everything including PRD creation, Ralph execution, progress tracking, and git integration.

### Alternative: Manual Command Line

If you prefer command-line usage:

#### 1. Create a PRD

Create a `prd.json` file with this structure:

```json
{
  "project": "MyApp",
  "branchName": "ralph/my-feature",
  "description": "Feature description",
  "userStories": [
    {
      "id": "1",
      "title": "Story title",
      "description": "What to build",
      "acceptanceCriteria": ["Criterion 1", "Criterion 2"],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

See `prd.json.example` for reference.

#### 2. Run Ralph

```bash
python ralph.py [max_iterations] [--config config.json]
```

Default is 10 iterations. Example:

```bash
# Use auto-detected LLM provider
python ralph.py 10

# Use specific config file
python ralph.py 15 --config my-llm-config.json

# Use backwards-compatible bash wrapper
./ralph.sh 10
```

#### What Ralph Does

On each iteration, Ralph will:
1. Create a feature branch (from PRD `branchName`)
2. Pick the highest priority story where `passes: false`
3. Spawn a fresh LLM instance with the prompt
4. Implement that single story
5. Run quality checks (typecheck, tests)
6. Commit if checks pass
7. Update `prd.json` to mark story as `passes: true`
8. Append learnings to `progress.txt`
9. Repeat until all stories pass or max iterations reached

When all stories have `passes: true`, Ralph outputs `<promise>COMPLETE</promise>` and exits.

## Key Files

| File | Purpose |
|------|---------|
| `ralph.py` | Main Python script - orchestrates the LLM loop |
| `ralph.sh` | Backwards-compatible bash wrapper (calls `ralph.py`) |
| `config.json` | LLM configuration (provider, model, API keys) |
| `requirements.txt` | Python dependencies (anthropic, ollama) |
| `prompt.md` | Instructions given to each LLM instance |
| `prd.json` | User stories with `passes` status (the task list) |
| `prd.json.example` | Example PRD format for reference |
| `progress.txt` | Append-only learnings for future iterations |
| `flowchart/` | Interactive visualization of how Ralph works |

## Flowchart

[![Ralph Flowchart](ralph-flowchart.png)](https://snarktank.github.io/ralph/)

**[View Interactive Flowchart](https://snarktank.github.io/ralph/)** - Click through to see each step with animations.

The `flowchart/` directory contains the source code. To run locally:

```bash
cd flowchart
npm install
npm run dev
```

## Critical Concepts

### Each Iteration = Fresh Context

Each iteration spawns a **new LLM instance** with clean context. The only memory between iterations is:
- Git history (commits from previous iterations)
- `progress.txt` (learnings and context)
- `prd.json` (which stories are done)

This applies to all providers (Amp, Claude API, Ollama).

### Small Tasks

Each PRD item should be small enough to complete in one context window. If a task is too big, the LLM runs out of context before finishing and produces poor code.

Right-sized stories:
- Add a database column and migration
- Add a UI component to an existing page
- Update a server action with new logic
- Add a filter dropdown to a list

Too big (split these):
- "Build the entire dashboard"
- "Add authentication"
- "Refactor the API"

### Progress Tracking and Learnings

After each iteration, Ralph appends learnings to `progress.txt`. This file is included in subsequent iterations so the LLM can learn from previous attempts.

**When using Amp:** Ralph also updates `AGENTS.md` files since Amp automatically reads them.

Examples of what gets recorded:
- Patterns discovered ("this codebase uses X for Y")
- Gotchas ("do not forget to update Z when changing W")
- Useful context ("the settings panel is in component X")
- Error resolutions and workarounds

### Feedback Loops

Ralph only works if there are feedback loops:
- Typecheck catches type errors
- Tests verify behavior
- CI must stay green (broken code compounds across iterations)

### Browser Verification for UI Stories

Frontend stories should include browser verification in acceptance criteria when possible.

**When using Amp:** Use "Verify in browser using dev-browser skill" in acceptance criteria and Ralph will automatically verify changes in the browser.

**When using Claude/Ollama:** Manual verification may be required, or implement custom browser automation tools.

### Stop Condition

When all stories have `passes: true`, Ralph outputs `<promise>COMPLETE</promise>` and the loop exits.

## Debugging

Check current state:

```bash
# See which stories are done
cat prd.json | jq '.userStories[] | {id, title, passes}'

# See learnings from previous iterations
cat progress.txt

# Check git history
git log --oneline -10
```

## Customizing prompt.md

Edit `prompt.md` to customize Ralph's behavior for your project:
- Add project-specific quality check commands
- Include codebase conventions
- Add common gotchas for your stack

## Archiving

Ralph automatically archives previous runs when you start a new feature (different `branchName`). Archives are saved to `archive/YYYY-MM-DD-feature-name/`.

## LLM Provider Notes

### Ollama (Recommended for Local/Free)
- Run `ollama pull llama3.1` to download the model
- Start Ollama: `ollama serve`
- Ralph auto-detects at `http://localhost:11434`
- Cost: Free (runs locally)
- Speed: Fast (depends on your hardware)

### Claude API
- Sign up at [console.anthropic.com](https://console.anthropic.com/)
- Set `ANTHROPIC_API_KEY` environment variable
- Recommended model: `claude-3-5-sonnet-20241022`
- Cost: Pay per token (see Anthropic pricing)
- Speed: Fast (API calls)

### Amp CLI
- Install from [ampcode.com](https://ampcode.com)
- Authenticate via CLI
- Ralph will use `amp` command
- Cost: Depends on Amp pricing
- Speed: Fast (CLI integration)

## References

- [Geoffrey Huntley's Ralph article](https://ghuntley.com/ralph/)
- [Edna PRD Planning Tool](https://github.com/wembassyco/edna)
- [Amp documentation](https://ampcode.com/manual)
- [Anthropic Claude API](https://www.anthropic.com/api)
- [Ollama](https://ollama.ai/)
