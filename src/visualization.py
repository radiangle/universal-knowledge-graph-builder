import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any
import networkx as nx
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import random


class GraphVisualizer:
    def __init__(self):
        self.color_map = {
            'entity': '#ff6b6b',
            'concept': '#4ecdc4', 
            'topic': '#45b7d1',
            'default': '#95a5a6'
        }
    
    def create_plotly_graph(self, graph_data: Dict[str, Any]) -> go.Figure:
        """Create interactive Plotly network graph"""
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        if not nodes:
            fig = go.Figure()
            fig.add_annotation(text="No graph data available", 
                             xref="paper", yref="paper", 
                             x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Create NetworkX graph for layout calculation
        G = nx.Graph()
        for node in nodes:
            G.add_node(node['id'], **node)
        
        for edge in edges:
            G.add_edge(edge['source'], edge['target'], **edge)
        
        # Calculate layout
        try:
            pos = nx.spring_layout(G, k=3, iterations=50)
        except:
            pos = {node['id']: (random.random(), random.random()) for node in nodes}
        
        # Prepare node traces
        node_x, node_y, node_text, node_colors, node_sizes = [], [], [], [], []
        
        for node in nodes:
            x, y = pos.get(node['id'], (0, 0))
            node_x.append(x)
            node_y.append(y)
            
            # Node text with hover info
            mentions = node.get('mentions_count', 0)
            node_text.append(
                f"<b>{node['label']}</b><br>"
                f"Type: {node.get('type', 'unknown')}<br>"
                f"Importance: {node.get('importance', 0):.2f}<br>"
                f"Mentions: {mentions}"
            )
            
            # Node color based on type
            node_colors.append(self.color_map.get(node.get('type'), self.color_map['default']))
            
            # Node size based on importance and mentions
            size = max(10, min(50, (node.get('importance', 0.5) * 30 + mentions * 5)))
            node_sizes.append(size)
        
        # Prepare edge traces
        edge_x, edge_y = [], []
        edge_info = []
        
        for edge in edges:
            x0, y0 = pos.get(edge['source'], (0, 0))
            x1, y1 = pos.get(edge['target'], (0, 0))
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            edge_info.append(
                f"{edge['source']} → {edge['target']}<br>"
                f"Type: {edge.get('type', 'relates_to')}<br>"
                f"Strength: {edge.get('strength', 0):.2f}"
            )
        
        # Create figure
        fig = go.Figure()
        
        # Add edges
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(width=1, color='rgba(125,125,125,0.5)'),
            hoverinfo='none',
            showlegend=False
        ))
        
        # Add nodes
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=2, color='white'),
                opacity=0.8
            ),
            text=[node['label'] for node in nodes],
            textposition="middle center",
            textfont=dict(size=10, color='white'),
            hoverinfo='text',
            hovertext=node_text,
            showlegend=False
        ))
        
        # Update layout
        fig.update_layout(
            title="Knowledge Graph",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Drag to pan, scroll to zoom, hover for details",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002,
                    xanchor="left", yanchor="bottom",
                    font=dict(color="gray", size=12)
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='rgba(0,0,0,0)',
            height=600
        )
        
        return fig
    
    def create_agraph_visualization(self, graph_data: Dict[str, Any]) -> None:
        """Create streamlit-agraph visualization"""
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        if not nodes:
            st.info("No graph data to visualize")
            return
        
        # Convert to agraph format
        agraph_nodes = []
        for node in nodes:
            color = self.color_map.get(node.get('type'), self.color_map['default'])
            size = max(20, min(60, node.get('importance', 0.5) * 50))
            
            agraph_nodes.append(Node(
                id=node['id'],
                label=node['label'],
                size=size,
                color=color,
                title=f"Type: {node.get('type', 'unknown')}\nImportance: {node.get('importance', 0):.2f}"
            ))
        
        agraph_edges = []
        for edge in edges:
            width = max(1, edge.get('strength', 0.5) * 5)
            agraph_edges.append(Edge(
                source=edge['source'],
                target=edge['target'],
                width=width,
                color='gray'
            ))
        
        # Configuration
        config = Config(
            width=800,
            height=600,
            directed=True,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6"
        )
        
        # Display graph
        selected = agraph(nodes=agraph_nodes, edges=agraph_edges, config=config)
        
        # Show selected node info
        if selected:
            st.sidebar.subheader("Selected Node")
            st.sidebar.json(selected)
    
    def display_graph_stats(self, graph_data: Dict[str, Any]) -> None:
        """Display graph statistics"""
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Nodes", len(nodes))
        
        with col2:
            st.metric("Total Edges", len(edges))
        
        with col3:
            node_types = {}
            for node in nodes:
                node_type = node.get('type', 'unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1
            st.metric("Node Types", len(node_types))
        
        with col4:
            if nodes:
                avg_importance = sum(node.get('importance', 0) for node in nodes) / len(nodes)
                st.metric("Avg Importance", f"{avg_importance:.2f}")
        
        # Node type distribution
        if nodes:
            st.subheader("Node Type Distribution")
            type_counts = {}
            for node in nodes:
                node_type = node.get('type', 'unknown')
                type_counts[node_type] = type_counts.get(node_type, 0) + 1
            
            fig_pie = px.pie(
                values=list(type_counts.values()),
                names=list(type_counts.keys()),
                color_discrete_map=self.color_map
            )
            st.plotly_chart(fig_pie, use_container_width=True)