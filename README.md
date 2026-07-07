# ARCS — Advanced Research & Curation System

A sophisticated, multi-agent AI research pipeline with an elegant web interface. This system orchestrates specialized agents to conduct comprehensive research on any topic.

## Features

- **Search Agent**: Scans the web for authoritative intelligence and current information
- **Reader Agent**: Extracts deep insights and synthesizes key findings  
- **Writer Agent**: Composes publication-ready research reports
- **Critic Agent**: Evaluates reports with rigorous editorial standards

## Project Structure

```
Multi-Agent-System/
├── index.html          # Main web interface (React-based)
├── styles.css          # Global styles and animations
├── pipeline.jsx        # Original React component (reference)
├── agents.py           # Python backend (Groq AI agents)
├── tools.py            # Tool definitions (web search, URL scraping)
├── pipeline.py         # Python pipeline execution
├── requirements.txt    # Python dependencies
└── .env               # Environment variables (API keys)
```

## Setup Instructions

### Option 1: Web Interface (HTML + React)

1. **Open in Browser**: Simply open `index.html` in a modern web browser
   - Chrome, Safari, Firefox, or Edge all work perfectly
   - No build process required—uses CDN for dependencies

2. **Configure API Key**:
   - When you click "Research", you'll be prompted for your **Anthropic API key**
   - Get one from: https://console.anthropic.com/
   - The key is only used for that session (not stored)

3. **Enter Research Topic**:
   - Type your topic in the input field
   - Press Enter or click "Research"
   - Watch the pipeline execute in real-time

4. **View Results**:
   - Track progress across 4 research stages
   - Expand individual stage results by clicking "VIEW"
   - Download final report by clicking "Copy Report"

### Option 2: Python Backend

1. **Install Dependencies**:
   ```bash
   cd Multi-Agent-System
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   - Ensure `.env` contains your API keys:
     ```
     GROQ_API_KEY=your_groq_key
     TAVILY_API_KEY=your_tavily_key
     ```

3. **Run Research Pipeline**:
   ```bash
   python pipeline.py
   ```

4. **Interactive Mode**:
   - Enter your research topic when prompted
   - The system will process through all 4 agents
   - Results display in the terminal

## API Keys Required

### For Web Interface (HTML):
- **Anthropic API Key**: https://console.anthropic.com/
  - Model: Claude Sonnet 4 (2025-05-14)
  - Web search enabled

### For Python Backend:
- **Groq API Key**: https://console.groq.com/
- **Tavily Search API Key**: https://tavily.com/

## Technology Stack

### Frontend
- React 18 (via CDN)
- Lucide Icons for UI elements
- Custom CSS animations
- Babel for JSX transpilation

### Backend
- Python 3.13+
- LangChain framework
- Groq (llama-3.3-70b-versatile)
- Tavily Search API
- BeautifulSoup for web scraping

## Browser Compatibility

✅ Chrome/Chromium 90+
✅ Safari 14+
✅ Firefox 88+
✅ Edge 90+

## Usage Tips

1. **Clear Topics**: Be specific for better research results
   - ✅ "How quantum computing is revolutionizing cryptography"
   - ❌ "quantum computing"

2. **Monitor Progress**: Watch the visual progress rail to track execution

3. **Expand Results**: Click "VIEW" on each stage to see intermediate findings

4. **Copy Reports**: Use the "Copy Report" button to save the final analysis

5. **Start New Research**: Click "New Research" to start a different topic

## Performance Notes

- Initial API calls may take 30-60 seconds per stage
- Larger topics may require longer processing
- Web search stage is typically slowest
- All requests are made to official Anthropic/Groq APIs

## Styling & Customization

- **Theme**: Dark mode with amber/gold accents
- **Fonts**: Cormorant Garamond (serif), IBM Plex Mono (code), Instrument Sans (UI)
- **Colors**: 
  - Primary: #eae4d8 (text)
  - Accent: #dfa020 (amber/gold)
  - Success: #58b064 (green)
  - Error: #c84040 (red)

Edit `styles.css` to customize colors and animations.

## Troubleshooting

### "API error 401"
- Your API key is invalid or expired
- Verify the key on the respective provider's dashboard
- Try generating a new key

### "Pipeline error"
- Check your internet connection
- Ensure API key has sufficient credits
- Try with a simpler research topic

### Styles not loading
- Clear your browser cache (Cmd+Shift+R or Ctrl+Shift+R)
- Check browser console for errors (F12 → Console)
- Verify styles.css is in the same directory as index.html

### React not rendering
- Check browser console for errors
- Verify you're using a modern browser
- Ensure JavaScript is enabled

## License

Licensed under Apache License 2.0
Copyright © 2024 ARCS Contributors

## Support

For issues or questions:
1. Check the browser console (F12 → Console)
2. Verify all API keys are correct
3. Try a simpler research topic
4. Ensure stable internet connection

---

**Happy researching!** 🔬✨
