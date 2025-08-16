# Universal Knowledge Graph Builder

Transform document archives into interactive, visual knowledge graphs with natural language Q&A capabilities.

## Features

- 📄 **Document Ingestion**: Upload text files or scrape web content
- 🧠 **AI-Powered Extraction**: Uses GPT-4 to identify concepts and relationships
- 🕸️ **Interactive Visualization**: Neo4j-powered graph with Plotly/Agraph display
- ❓ **Natural Language Q&A**: Ask questions about your documents
- 📊 **Graph Analytics**: View statistics and insights about your knowledge graph

## Tech Stack

- **Frontend**: Streamlit
- **Graph Database**: Neo4j
- **Visualization**: Plotly, streamlit-agraph
- **NLP**: OpenAI GPT-4 API
- **Backend**: Python with NetworkX

## Quick Start

### Prerequisites

1. **Neo4j Database**:
   - Install Neo4j Desktop or use Neo4j AuraDB (free tier)
   - Start your Neo4j instance
   - Note your connection details (URI, username, password)

2. **OpenAI API Key**:
   - Get an API key from OpenAI
   - Ensure you have GPT-4 access

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/universal-knowledge-graph-builder.git
cd universal-knowledge-graph-builder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
OPENAI_API_KEY=your_openai_api_key_here
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
```

### Running the Application

```bash
streamlit run app.py
```

Navigate to `http://localhost:8501` in your browser.

## Usage

### 1. Connect to Neo4j
- Click "Connect to Neo4j" in the sidebar
- Verify connection is successful

### 2. Process Documents
- Upload text files (TXT format)
- Or enter URLs for web scraping
- Click "Process Documents"

### 3. Visualize Graph
- Switch to "Graph Visualization" tab
- View interactive network graph
- Explore graph statistics

### 4. Ask Questions
- Go to "Q&A Interface" tab
- Ask natural language questions
- Get AI-powered answers with source citations

## Architecture

```
src/
├── ingestion.py      # Document processing and chunking
├── graph_builder.py  # Neo4j graph creation with GPT-4
├── visualization.py  # Interactive graph display
└── qa_engine.py      # Q&A system with context retrieval
```

## Neo4j Graph Schema

- **Nodes**:
  - `Concept`: Extracted concepts/entities
  - `DocumentChunk`: Text chunks from documents

- **Relationships**:
  - `MENTIONS`: Links chunks to concepts
  - `RELATES_TO`: Semantic relationships between concepts

## Deployment

### Streamlit Community Cloud

1. Push to GitHub
2. Connect to Streamlit Cloud
3. Set environment variables in Streamlit dashboard
4. Deploy!

### Manual Deployment

The app can be deployed on any platform supporting Python:
- Heroku
- Railway
- Render
- Google Cloud Run
- AWS ECS

## Performance Tips

- Use Neo4j AuraDB for better performance
- Limit document size for faster processing
- Consider using embedding-based similarity for better Q&A results

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions, please open a GitHub issue or contact the maintainers.