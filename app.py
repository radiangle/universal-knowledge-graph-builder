import streamlit as st
import os
from dotenv import load_dotenv
from src.ingestion import DocumentProcessor
from src.graph_builder import Neo4jGraphBuilder
from src.visualization import GraphVisualizer
from src.qa_engine import QAEngine

# Load environment variables from .env file in current directory
load_dotenv(override=True)

# Page configuration
st.set_page_config(
    page_title="Universal Knowledge Graph Builder",
    page_icon="🧠",
    layout="wide"
)

def init_session_state():
    """Initialize session state variables"""
    if 'graph_builder' not in st.session_state:
        st.session_state.graph_builder = None
    if 'qa_engine' not in st.session_state:
        st.session_state.qa_engine = None
    if 'graph_data' not in st.session_state:
        st.session_state.graph_data = {'nodes': [], 'edges': []}
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False

def connect_to_neo4j():
    """Initialize Neo4j connection"""
    try:
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        neo4j_username = os.getenv('NEO4J_USERNAME', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', '')
        
        if not neo4j_password:
            st.error("Please set NEO4J_PASSWORD in your environment variables")
            st.stop()
        
        graph_builder = Neo4jGraphBuilder(neo4j_uri, neo4j_username, neo4j_password)
        qa_engine = QAEngine(graph_builder.driver)
        
        return graph_builder, qa_engine
    
    except Exception as e:
        st.error(f"Failed to connect to Neo4j: {str(e)}")
        st.info("Make sure Neo4j is running and credentials are correct")
        st.stop()

def main():
    init_session_state()
    
    # Header
    st.title("🧠 Universal Knowledge Graph Builder")
    st.markdown("Transform documents into interactive knowledge graphs with AI-powered Q&A")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key check
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            st.error("Please set OPENAI_API_KEY environment variable")
            st.stop()
        else:
            # Show partial key for verification
            masked_key = f"{openai_key[:7]}...{openai_key[-4:]}" if len(openai_key) > 11 else "***"
            st.success(f"✅ OpenAI API Key configured: {masked_key}")
        
        # Neo4j connection
        if st.button("🔌 Connect to Neo4j"):
            with st.spinner("Connecting to Neo4j..."):
                st.session_state.graph_builder, st.session_state.qa_engine = connect_to_neo4j()
                st.success("✅ Connected to Neo4j")
        
        # Clear database button
        if st.session_state.graph_builder:
            if st.button("🗑️ Clear Database", type="secondary"):
                st.session_state.graph_builder.clear_database()
                st.session_state.graph_data = {'nodes': [], 'edges': []}
                st.session_state.processing_complete = False
                st.success("Database cleared")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📄 Document Processing", "🕸️ Graph Visualization", "❓ Q&A Interface"])
    
    with tab1:
        st.header("Document Ingestion")
        
        # Sample data option
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Quick Start with Sample Data")
        with col2:
            if st.button("📚 Load Sample Data", type="secondary"):
                if not st.session_state.graph_builder:
                    st.error("Please connect to Neo4j first")
                else:
                    load_sample_data()
        
        st.divider()
        
        # File upload
        uploaded_files = st.file_uploader(
            "Upload text files",
            type=['txt'],
            accept_multiple_files=True,
            help="Upload text files to build your knowledge graph"
        )
        
        # URL input
        st.subheader("Or scrape from URLs")
        urls_text = st.text_area(
            "Enter URLs (one per line)",
            placeholder="https://example.com/article1\nhttps://example.com/article2"
        )
        
        # Processing button
        if st.button("🚀 Process Documents", type="primary"):
            if not st.session_state.graph_builder:
                st.error("Please connect to Neo4j first")
            elif not uploaded_files and not urls_text.strip():
                st.warning("Please upload files or enter URLs")
            else:
                process_documents(uploaded_files, urls_text)
    
    with tab2:
        st.header("Knowledge Graph Visualization")
        
        if st.session_state.processing_complete and st.session_state.graph_builder:
            # Get latest graph data
            if st.button("🔄 Refresh Graph"):
                st.session_state.graph_data = st.session_state.graph_builder.get_graph_data()
            
            # Display graph
            visualizer = GraphVisualizer()
            
            # Graph statistics
            visualizer.display_graph_stats(st.session_state.graph_data)
            
            # Visualization options
            viz_type = st.selectbox("Visualization Type", ["Plotly", "Agraph"])
            
            if viz_type == "Plotly":
                fig = visualizer.create_plotly_graph(st.session_state.graph_data)
                st.plotly_chart(fig, use_container_width=True)
            else:
                visualizer.create_agraph_visualization(st.session_state.graph_data)
        
        else:
            st.info("Process some documents first to see the knowledge graph")
    
    with tab3:
        st.header("Q&A Interface")
        
        if st.session_state.processing_complete and st.session_state.qa_engine:
            # Question suggestions
            col1, col2 = st.columns([3, 1])
            
            with col1:
                question = st.text_input(
                    "Ask a question about your documents:",
                    placeholder="What are the main concepts discussed?"
                )
            
            with col2:
                if st.button("💡 Suggestions"):
                    suggestions = st.session_state.qa_engine.get_question_suggestions()
                    for i, suggestion in enumerate(suggestions):
                        if st.button(f"📝 {suggestion}", key=f"suggestion_{i}"):
                            question = suggestion
            
            # Answer question
            if st.button("🤔 Get Answer", type="primary") and question:
                with st.spinner("Thinking..."):
                    answer_data = st.session_state.qa_engine.answer_question(question)
                    
                    # Display answer
                    st.subheader("Answer")
                    st.write(answer_data['answer'])
                    
                    # Display confidence
                    confidence = answer_data['confidence']
                    st.metric("Confidence Score", f"{confidence:.2f}")
                    
                    # Show relevant concepts
                    if answer_data['relevant_nodes']:
                        st.subheader("Relevant Concepts")
                        concepts = [node['name'] for node in answer_data['relevant_nodes'][:10]]
                        st.write(", ".join(concepts))
                    
                    # Show sources
                    if answer_data['context_sources']:
                        with st.expander("View Sources"):
                            for i, source in enumerate(answer_data['context_sources']):
                                st.write(f"**Source {i+1}:** {source.get('source', 'Unknown')}")
                                st.write(f"*Related to: {source.get('related_concept', 'N/A')}*")
                                st.write(source.get('text', '')[:300] + "...")
                                st.divider()
        
        else:
            st.info("Process some documents first to enable Q&A")

def load_sample_data():
    """Load and process the sample_data.txt file"""
    try:
        sample_file_path = "sample_data.txt"
        with open(sample_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        processor = DocumentProcessor()
        chunks = processor.process_text_file(content)
        
        if chunks:
            st.success(f"Loaded sample data: {len(chunks)} text chunks")
            
            # Build graph
            with st.spinner("Building knowledge graph from sample data... This may take a few minutes."):
                st.session_state.graph_builder.build_graph_from_chunks(chunks)
            
            # Get graph data for visualization
            st.session_state.graph_data = st.session_state.graph_builder.get_graph_data()
            st.session_state.processing_complete = True
            
            st.success("✅ Sample knowledge graph built successfully!")
            st.info("Switch to the 'Graph Visualization' or 'Q&A Interface' tabs to explore")
        else:
            st.error("Failed to process sample data")
            
    except FileNotFoundError:
        st.error("Sample data file not found")
    except Exception as e:
        st.error(f"Error loading sample data: {str(e)}")

def process_documents(uploaded_files, urls_text):
    """Process uploaded files and URLs"""
    processor = DocumentProcessor()
    all_chunks = []
    
    # Process uploaded files
    if uploaded_files:
        for file in uploaded_files:
            content = file.read().decode('utf-8')
            if processor.validate_file_size(content):
                chunks = processor.process_text_file(content)
                all_chunks.extend(chunks)
            else:
                st.warning(f"File {file.name} is too large (>100MB)")
    
    # Process URLs
    if urls_text.strip():
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        for url in urls:
            chunks = processor.process_url(url)
            all_chunks.extend(chunks)
    
    if all_chunks:
        st.success(f"Successfully processed {len(all_chunks)} text chunks")
        
        # Build graph
        with st.spinner("Building knowledge graph... This may take a few minutes."):
            st.session_state.graph_builder.build_graph_from_chunks(all_chunks)
        
        # Get graph data for visualization
        st.session_state.graph_data = st.session_state.graph_builder.get_graph_data()
        st.session_state.processing_complete = True
        
        st.success("✅ Knowledge graph built successfully!")
        st.info("Switch to the 'Graph Visualization' or 'Q&A Interface' tabs to explore your graph")
    
    else:
        st.error("No valid content found to process")

if __name__ == "__main__":
    main()