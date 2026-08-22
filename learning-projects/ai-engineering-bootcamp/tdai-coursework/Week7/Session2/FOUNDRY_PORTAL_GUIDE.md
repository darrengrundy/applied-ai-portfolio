# Demo 1: Testing Voice Agent in the Azure AI Foundry Portal

**Goal:** Validate the agent's logic and voice configuration in a low-code environment
**Key Takeaway:** Testing in the portal proves your cloud configuration is correct before you write a single line of code

---

## Step-by-Step

### 1. Create a Project
- Go to [https://ai.azure.com](https://ai.azure.com)
- Click **+ New project** → give it a name (e.g. `tdai-voice-demo`)
- Select your existing hub/resource (australiaeast)

### 2. Create an Agent
- In the left sidebar go to **Agents**
- Click **+ New agent**
- Give it a name (e.g. `TDAI Voice Assistant`)
- Under **Model**, select `gpt-4o` (or `gpt-4o-mini`)

### 3. Set System Instructions
In the **Instructions** box, enter something like:

```
You are a helpful AI assistant for TDAI Bank.
You answer questions about account balances, transactions, and banking services.
Keep responses short and clear — this is a voice interface.
```

### 4. Enable Voice Mode
- Look for the **Voice** toggle or **Voice Mode** button in the agent playground (top-right of the chat panel)
- Click it to enable voice interaction
- Select a voice profile (e.g. **Alloy**, **Nova**, **Echo**)

### 5. Start a Session and Speak
- Click **Start session** (or the microphone button)
- Allow microphone access if prompted
- Speak into your microphone — try:
  - *"Hello, who are you?"*
  - *"What's my account balance?"*
  - *"What services do you offer?"*
- The agent will respond in real-time using the selected voice

### 6. Note Your Agent Details
> **Important for Demo 2** — before leaving the portal, copy these values:

| Value | Where to find it |
|---|---|
| **Agent ID** | Agents page → click your agent → Details tab |
| **Agent Name** | The name you gave it |
| **Project Endpoint** | Project settings → Overview |

---

## What This Demonstrates
- The **"brain"** (GPT-4o) and the **"voice"** are both working in the cloud
- If something is wrong in code later, you can rule out cloud config as the issue
- Voice Mode in Foundry uses the same underlying **Azure Voice Live** infrastructure as the SDK you'll use in Demo 2
