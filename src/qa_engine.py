import openai
import os
from typing import List, Dict, Any, Tuple
from neo4j import GraphDatabase
import streamlit as st

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


class QAEngine:
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        openai.api_key = os.getenv('OPENAI_API_KEY')
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """Answer a question using the knowledge graph"""
        try:
            # Find relevant nodes and context
            relevant_nodes = self._find_relevant_context(question)
            context_text = self._retrieve_context_text(relevant_nodes)
            
            # Generate answer using GPT-4
            answer = self._generate_answer(question, context_text, relevant_nodes)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(question, relevant_nodes, context_text)
            
            return {
                'answer': answer,
                'relevant_nodes': relevant_nodes,
                'context_sources': context_text[:3],  # Top 3 sources
                'confidence': confidence,
                'graph_highlights': [node['name'] for node in relevant_nodes[:10]]
            }
            
        except Exception as e:
            st.error(f"Error answering question: {str(e)}")
            return {
                'answer': "Sorry, I couldn't process your question.",
                'relevant_nodes': [],
                'context_sources': [],
                'confidence': 0.0,
                'graph_highlights': []
            }
    
    def _find_relevant_context(self, question: str) -> List[Dict[str, Any]]:
        """Find relevant nodes using multiple strategies"""
        with self.driver.session() as session:
            # Strategy 1: Direct keyword matching
            keywords = self._extract_keywords(question)
            keyword_nodes = []
            
            for keyword in keywords:
                result = session.run("""
                    MATCH (c:Concept)
                    WHERE toLower(c.name) CONTAINS toLower($keyword)
                    RETURN c.name as name, c.type as type, c.importance as importance,
                           COUNT {(c)<-[:MENTIONS]-()} as mentions_count
                    ORDER BY c.importance DESC
                    LIMIT 5
                    """, keyword=keyword)
                keyword_nodes.extend([dict(record) for record in result])
            
            # Strategy 2: Context expansion via relationships
            expanded_nodes = []
            for node in keyword_nodes[:5]:  # Expand top 5 nodes
                result = session.run("""
                    MATCH (c:Concept {name: $name})-[r:RELATES_TO]-(related:Concept)
                    RETURN related.name as name, related.type as type, 
                           related.importance as importance, r.strength as relation_strength
                    ORDER BY r.strength DESC
                    LIMIT 3
                    """, name=node['name'])
                expanded_nodes.extend([dict(record) for record in result])
            
            # Combine and deduplicate
            all_nodes = keyword_nodes + expanded_nodes
            seen = set()
            unique_nodes = []
            for node in all_nodes:
                if node['name'] not in seen:
                    seen.add(node['name'])
                    unique_nodes.append(node)
            
            # Sort by relevance score
            for node in unique_nodes:
                node['relevance_score'] = (
                    node.get('importance', 0.5) * 0.6 +
                    min(node.get('mentions_count', 0) / 10, 1.0) * 0.3 +
                    node.get('relation_strength', 0.5) * 0.1
                )
            
            return sorted(unique_nodes, key=lambda x: x['relevance_score'], reverse=True)[:15]
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract relevant keywords from question"""
        # Simple keyword extraction - could be enhanced with NLP
        import re
        
        # Remove common question words
        stop_words = {'what', 'how', 'why', 'when', 'where', 'who', 'which', 
                     'is', 'are', 'was', 'were', 'do', 'does', 'did', 'can', 'could',
                     'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
                     'for', 'of', 'with', 'by', 'about', 'tell', 'me', 'explain'}
        
        words = re.findall(r'\b\w+\b', question.lower())
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        
        # Add potential multi-word phrases
        phrases = re.findall(r'\b\w+\s+\w+\b', question.lower())
        keywords.extend(phrases)
        
        return keywords[:10]  # Limit to top 10
    
    def _retrieve_context_text(self, relevant_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Retrieve source text for relevant nodes"""
        context_texts = []
        
        with self.driver.session() as session:
            for node in relevant_nodes[:10]:  # Top 10 nodes
                result = session.run("""
                    MATCH (c:Concept {name: $name})<-[:MENTIONS]-(doc:DocumentChunk)
                    RETURN doc.text as text, doc.source as source, 
                           doc.chunk_index as chunk_index
                    ORDER BY doc.chunk_index
                    LIMIT 3
                    """, name=node['name'])
                
                for record in result:
                    context_texts.append({
                        'text': record['text'],
                        'source': record['source'],
                        'chunk_index': record['chunk_index'],
                        'related_concept': node['name']
                    })
        
        # Sort by relevance and deduplicate
        seen_texts = set()
        unique_contexts = []
        for ctx in context_texts:
            text_hash = hash(ctx['text'][:100])  # Use first 100 chars as hash
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_contexts.append(ctx)
        
        return unique_contexts[:8]  # Top 8 unique contexts
    
    def _generate_answer(self, question: str, context_texts: List[Dict[str, Any]], 
                        relevant_nodes: List[Dict[str, Any]]) -> str:
        """Generate answer using GPT-4 with retrieved context"""
        if not context_texts:
            return "I don't have enough information to answer this question."
        
        # Prepare context
        context_str = "\n\n".join([
            f"Source: {ctx['source']} (chunk {ctx['chunk_index']})\n"
            f"Related to: {ctx['related_concept']}\n"
            f"Text: {ctx['text'][:500]}..."
            for ctx in context_texts
        ])
        
        concepts_str = ", ".join([node['name'] for node in relevant_nodes[:10]])
        
        prompt = f"""
        Based on the following context from documents and the identified concepts, 
        answer the user's question. Be specific and cite the sources when possible.
        
        Question: {question}
        
        Relevant Concepts: {concepts_str}
        
        Context:
        {context_str}
        
        Provide a clear, informative answer. If the context doesn't fully address 
        the question, mention what information is available and what might be missing.
        """
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a knowledgeable assistant that answers questions based on provided context. Be accurate and cite sources."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def _calculate_confidence(self, question: str, relevant_nodes: List[Dict[str, Any]], 
                            context_texts: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for the answer"""
        if not relevant_nodes or not context_texts:
            return 0.1
        
        # Factors affecting confidence
        factors = []
        
        # Number of relevant nodes found
        factors.append(min(len(relevant_nodes) / 10, 1.0) * 0.3)
        
        # Quality of context (based on text length and relevance)
        context_quality = sum([
            min(len(ctx['text']) / 1000, 1.0) for ctx in context_texts
        ]) / max(len(context_texts), 1)
        factors.append(context_quality * 0.3)
        
        # Average importance of relevant nodes
        if relevant_nodes:
            avg_importance = sum([node.get('importance', 0.5) for node in relevant_nodes]) / len(relevant_nodes)
            factors.append(avg_importance * 0.2)
        
        # Keyword coverage
        keywords = self._extract_keywords(question)
        node_names = [node['name'].lower() for node in relevant_nodes]
        keyword_coverage = sum([
            1 for keyword in keywords 
            if any(keyword in name for name in node_names)
        ]) / max(len(keywords), 1)
        factors.append(keyword_coverage * 0.2)
        
        return min(sum(factors), 1.0)
    
    def get_question_suggestions(self) -> List[str]:
        """Generate suggested questions based on graph content"""
        with self.driver.session() as session:
            # Get top concepts
            result = session.run("""
                MATCH (c:Concept)
                RETURN c.name as name, c.type as type, c.importance as importance
                ORDER BY c.importance DESC
                LIMIT 5
            """)
            
            top_concepts = [record['name'] for record in result]
            
            # Generate questions
            suggestions = []
            for concept in top_concepts[:3]:
                suggestions.extend([
                    f"What is {concept}?",
                    f"How does {concept} relate to other concepts?",
                    f"Tell me more about {concept}"
                ])
            
            # Add general questions
            suggestions.extend([
                "What are the main topics in this document?",
                "What relationships exist between concepts?",
                "Summarize the key information"
            ])
            
            return suggestions[:8]