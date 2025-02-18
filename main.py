import networkx as nx 
import os
from networkx.algorithms import community  
from cdlib.algorithms import leiden  
import json 
import os
import json
import requests
import networkx as nx
import os
import requests
import json
import os
import openai
from openai import OpenAI

client = OpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY")
)
#usage
response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct",
    temperature=0,
    messages=[{"role": "system", "content": "Extract entities and relationships from the following text."}, 
              {"role": "user", "content": "John is a software engineer at TechCorp."}]
)

print(response.choices[0].message.content)

openai.api_key = os.getenv("OPENAI_API_KEY")

client = openai
# TODO: Function to load pdfs and divide them into documents. Can start with 5-10 related papers lets say transformer paper and then papers which cited it and so on.
# Ensure DOCUMENTS is defined, e.g.:
DOCUMENTS = ["Sample document 1 text.", "Sample document 2 text."]

# 1. Source Documents → Text Chunks
def split_documents_into_chunks(documents, chunk_size=600, overlap_size=100):
    chunks = []
    for document in documents:
        for i in range(0, len(document), chunk_size - overlap_size):
            chunk = document[i:i + chunk_size]
            chunks.append(chunk)
    return chunks
# TODO: Identify what elements we want to extract. Experiment with the default prompt
# 2. Text Chunks → Element Instances
def extract_elements_from_chunks(chunks):
    elements = []
    for index, chunk in enumerate(chunks):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Extract entities and relationships from the following text."},
                {"role": "user", "content": chunk}
            ]
        )
        entities_and_relations = response.choices[0].message.content
        elements.append(entities_and_relations)
    return elements
# TODO: Identify how we want our graph to look like. Experiment with the default prompt
# 3. Element Instances → Element Summaries
def summarize_elements(elements):
    summaries = []
    for index, element in enumerate(elements):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Summarize the following entities and relationships in a structured format. Use \"->\" to represent relationships, after the \"Relationships:\" word."},
                {"role": "user", "content": element}
            ]
        )
        summary = response.choices[0].message.content
        summaries.append(summary)
    return summaries

# 4. Element Summaries → Graph Communities
def build_graph_from_summaries(summaries):
    G = nx.Graph()
    for summary in summaries:
        lines = summary.split("\n")
        entities_section = False
        relationships_section = False
        entities = []
        for line in lines:
            if line.startswith("### Entities:") or line.startswith("**Entities:**"):
                entities_section = True
                relationships_section = False
                continue
            elif line.startswith("### Relationships:") or line.startswith("**Relationships:**"):
                entities_section = False
                relationships_section = True
                continue
            if entities_section and line.strip():
                entity = line.split(".", 1)[1].strip() if line[0].isdigit() and line[1] == "." else line.strip()
                entity = entity.replace("**", "")
                entities.append(entity)
                G.add_node(entity)
            elif relationships_section and line.strip():
                parts = line.split("->")
                if len(parts) >= 2:
                    source = parts[0].strip()
                    target = parts[-1].strip()
                    relation = " -> ".join(parts[1:-1]).strip()
                    G.add_edge(source, target, label=relation)
    return G

def detect_communities(graph):
    communities = []
    for component in nx.connected_components(graph):
        subgraph = graph.subgraph(component)
        if len(subgraph.nodes) > 1:
            try:
                sub_communities = algorithms.leiden(subgraph)
                for community in sub_communities.communities:
                    communities.append(list(community))
            except Exception as e:
                print(f"Error processing community: {e}")
        else:
            communities.append(list(subgraph.nodes))
    return communities
# 5. Graph Communities → Community Summaries
def summarize_communities(communities, graph):
    community_summaries = []
    for index, community in enumerate(communities):
        subgraph = graph.subgraph(community)
        nodes = list(subgraph.nodes)
        edges = list(subgraph.edges(data=True))
        description = "Entities: " + ", ".join(nodes) + "\nRelationships: "
        relationships = []
        for edge in edges:
            relationships.append(
                f"{edge[0]} -> {edge[2]['label']} -> {edge[1]}")
        description += ", ".join(relationships)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Summarize the following community of entities and relationships."},
                {"role": "user", "content": description}
            ]
        )
        summary = response.choices[0].message.content.strip()
        community_summaries.append(summary)
    return community_summaries

# 6. Community Summaries → Community Answers → Global Answer
def generate_answers_from_communities(community_summaries, query):
    intermediate_answers = []
    for summary in community_summaries:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Answer the following query based on the provided summary."},
                {"role": "user", "content": f"Query: {query} Summary: {summary}"}
            ]
        )
        intermediate_answers.append(response.choices[0].message.content)

    final_response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Combine these answers into a final, concise response."},
            {"role": "user", "content": f"Intermediate answers: {intermediate_answers}"}
        ]
    )
    final_answer = final_response.choices[0].message.content
    return final_answer
# Main
def graph_rag_pipeline(documents, query, chunk_size=600, overlap_size=100):
    chunks = split_documents_into_chunks(documents, chunk_size, overlap_size)
    elements = extract_elements_from_chunks(chunks)
    summaries = summarize_elements(elements)
    graph = build_graph_from_summaries(summaries)
    communities = detect_communities(graph)
    community_summaries = summarize_communities(communities)
    final_answer = generate_answers_from_communities(community_summaries, query)
    return final_answer

# Example usage
query = "What are the main themes in these documents?"
answer = graph_rag_pipeline(DOCUMENTS, query)
print('Answer:', answer)
