import os
from typing import List, Dict, Any, Tuple
import openai
from neo4j import GraphDatabase
import json
import streamlit as st
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    # Continue without dotenv for cloud deployment
    pass
except Exception:
    # Continue without .env file for cloud deployment
    pass


class Neo4jGraphBuilder:
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Clear all nodes and relationships"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def extract_concepts_and_relationships(self, text_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Use GPT-4 to extract concepts and relationships from text"""
        try:
            prompt = f"""
            Analyze the following text and extract:
            1. Key concepts/entities (5-10 items)
            2. Relationships between these concepts
            3. Topic categories
            
            Text: {text_chunk['text'][:2000]}
            
            Return JSON format:
            {{
                "concepts": [
                    {{"name": "concept_name", "type": "entity|topic|concept", "importance": 0.1-1.0}}
                ],
                "relationships": [
                    {{"source": "concept1", "target": "concept2", "type": "relates_to|contains|mentions", "strength": 0.1-1.0}}
                ]
            }}
            """
            
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting knowledge graphs from text. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            result = json.loads(response.choices[0].message.content)
            result['source_chunk'] = text_chunk
            return result
            
        except Exception as e:
            st.error(f"Error extracting concepts: {str(e)}")
            return {"concepts": [], "relationships": [], "source_chunk": text_chunk}
    
    def build_graph_from_chunks(self, text_chunks: List[Dict[str, Any]]) -> None:
        """Process all chunks and build Neo4j graph"""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, chunk in enumerate(text_chunks):
            # Update status
            status_text.text(f"Processing chunk {i+1}/{len(text_chunks)}...")
            
            # Extract concepts and relationships
            extraction = self.extract_concepts_and_relationships(chunk)
            
            # Add to Neo4j
            self._add_to_neo4j(extraction)
            
            # Update progress
            progress_bar.progress((i + 1) / len(text_chunks))
        
        status_text.text("Graph building complete!")
        progress_bar.empty()
    
    def _add_to_neo4j(self, extraction: Dict[str, Any]) -> None:
        """Add extracted concepts and relationships to Neo4j"""
        with self.driver.session() as session:
            chunk_info = extraction['source_chunk']
            
            # Create document chunk node
            session.run("""
                MERGE (doc:DocumentChunk {id: $chunk_id})
                SET doc.text = $text,
                    doc.source = $source,
                    doc.chunk_index = $chunk_index,
                    doc.created_at = datetime()
                """,
                chunk_id=chunk_info['id'],
                text=chunk_info['text'],
                source=chunk_info['source'],
                chunk_index=chunk_info['chunk_index']
            )
            
            # Create concept nodes
            for concept in extraction['concepts']:
                session.run("""
                    MERGE (c:Concept {name: $name})
                    SET c.type = $type,
                        c.importance = $importance,
                        c.updated_at = datetime()
                    """,
                    name=concept['name'],
                    type=concept.get('type', 'concept'),
                    importance=concept.get('importance', 0.5)
                )
                
                # Link concept to document chunk
                session.run("""
                    MATCH (c:Concept {name: $concept_name})
                    MATCH (doc:DocumentChunk {id: $chunk_id})
                    MERGE (doc)-[:MENTIONS {strength: $importance}]->(c)
                    """,
                    concept_name=concept['name'],
                    chunk_id=chunk_info['id'],
                    importance=concept.get('importance', 0.5)
                )
            
            # Create relationships between concepts
            for rel in extraction['relationships']:
                session.run("""
                    MATCH (source:Concept {name: $source_name})
                    MATCH (target:Concept {name: $target_name})
                    MERGE (source)-[r:RELATES_TO {type: $rel_type}]->(target)
                    SET r.strength = $strength,
                        r.updated_at = datetime()
                    """,
                    source_name=rel['source'],
                    target_name=rel['target'],
                    rel_type=rel.get('type', 'relates_to'),
                    strength=rel.get('strength', 0.5)
                )
    
    def get_graph_data(self) -> Dict[str, Any]:
        """Retrieve graph data for visualization"""
        with self.driver.session() as session:
            # Get nodes
            nodes_result = session.run("""
                MATCH (c:Concept)
                RETURN c.name as name, c.type as type, c.importance as importance,
                       COUNT {(c)<-[:MENTIONS]-()} as mentions_count
            """)
            
            nodes = [
                {
                    'id': record['name'],
                    'label': record['name'],
                    'type': record['type'],
                    'importance': record['importance'],
                    'mentions_count': record['mentions_count']
                }
                for record in nodes_result
            ]
            
            # Get relationships
            rels_result = session.run("""
                MATCH (source:Concept)-[r:RELATES_TO]->(target:Concept)
                RETURN source.name as source, target.name as target, 
                       r.type as type, r.strength as strength
            """)
            
            edges = [
                {
                    'source': record['source'],
                    'target': record['target'],
                    'type': record['type'],
                    'strength': record['strength']
                }
                for record in rels_result
            ]
            
            return {'nodes': nodes, 'edges': edges}
    
    def find_relevant_nodes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find concepts relevant to a query using text similarity"""
        with self.driver.session() as session:
            # Simple text matching for now - could be enhanced with embeddings
            result = session.run("""
                MATCH (c:Concept)
                WHERE toLower(c.name) CONTAINS toLower($query)
                   OR EXISTS {
                       MATCH (c)<-[:MENTIONS]-(doc:DocumentChunk)
                       WHERE toLower(doc.text) CONTAINS toLower($query)
                   }
                RETURN c.name as name, c.type as type, c.importance as importance
                ORDER BY c.importance DESC
                LIMIT $limit
                """,
                query=query,
                limit=limit
            )
            
            return [dict(record) for record in result]