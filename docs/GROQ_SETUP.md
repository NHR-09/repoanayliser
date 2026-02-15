# Using Groq as LLM Provider

## Why Groq?

- **Fast**: Ultra-low latency inference
- **Free Tier**: Generous free API access
- **Powerful**: Llama 3.1 70B model
- **Simple**: OpenAI-compatible API

## Setup

### 1. Get Groq API Key

1. Visit https://console.groq.com
2. Sign up for free account
3. Navigate to API Keys section
4. Create new API key
5. Copy the key (starts with `gsk_...`)

### 2. Configure Environment

Edit `.env` file:
```bash
GROQ_API_KEY=gsk_your_actual_key_here
```

### 3. Verify Setup

```bash
python init_system.py
```

Should show: `✅ Groq API key found`

## Model Used

**llama-3.1-70b-versatile**
- 70 billion parameters
- Fast inference on Groq hardware
- Excellent for code understanding
- Context window: 8K tokens

## API Limits (Free Tier)

- 30 requests per minute
- 6,000 tokens per minute
- Sufficient for hackathon demo

## Alternative Models

Edit `src/reasoning/llm_reasoner.py` to change model:

```python
model="llama-3.1-8b-instant"  # Faster, smaller
model="mixtral-8x7b-32768"    # Larger context
model="llama-3.1-70b-versatile"  # Default (best)
```

## Testing

```bash
# Test LLM integration
curl -X POST http://localhost:8000/analyze \
  -d '{"repo_url": "https://github.com/pallets/flask"}'

# Wait for completion, then:
curl http://localhost:8000/architecture
```

Should return AI-generated explanation.

## Troubleshooting

### "API key not found"
- Check `.env` file exists
- Verify `GROQ_API_KEY` is set
- Restart server after changing `.env`

### "Rate limit exceeded"
- Wait 60 seconds
- Free tier: 30 requests/minute
- Upgrade at console.groq.com

### "Model not found"
- Check model name spelling
- Available models: https://console.groq.com/docs/models

## Advantages Over OpenAI/Anthropic

| Feature | Groq | OpenAI | Anthropic |
|---------|------|--------|-----------|
| Speed | ⚡ Ultra-fast | Medium | Medium |
| Free Tier | ✅ Generous | Limited | Limited |
| Setup | Easy | Requires billing | Requires billing |
| Latency | <1s | 2-5s | 2-5s |

Perfect for hackathon demos! 🚀
