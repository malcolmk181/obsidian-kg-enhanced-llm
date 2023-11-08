"""
graph_handling.py

Contains functions & classes for creating graphs and pulling information from them.
"""
from typing import List, Optional

from dotenv import load_dotenv
from langchain.chains.openai_functions import create_structured_output_chain
from langchain.chat_models import ChatOpenAI
from langchain.graphs import Neo4jGraph
from langchain.graphs.graph_document import (
    Node as BaseNode,
    Relationship as BaseRelationship,
)
from langchain.prompts import ChatPromptTemplate
from langchain.pydantic_v1 import BaseModel, Field
from langchain.schema import Document
from tqdm import tqdm

import embedding_handling
import file_handling


load_dotenv()
# OPENAI_API_KEY in .env file


GPT3_TURBO = ChatOpenAI(model="gpt-3.5-turbo-1106", temperature=0)
GPT4_TURBO = ChatOpenAI(model="gpt-4-1106-preview", temperature=0)

GPT3 = ChatOpenAI(model="gpt-3.5-turbo-16k", temperature=0)
GPT4 = ChatOpenAI(model="gpt-4", temperature=0)

NEO4J_URL = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "athena_password"


class Property(BaseModel):
    """A single property consisting of key and value"""

    key: str = Field(..., description="key")
    value: str = Field(..., description="value")


class Node(BaseNode):
    properties: Optional[List[Property]] = Field(
        None, description="List of node properties"
    )


class Relationship(BaseRelationship):
    properties: Optional[List[Property]] = Field(
        None, description="List of relationship properties"
    )


class KnowledgeGraph(BaseModel):
    """Generate a knowledge graph with entities and relationships."""

    nodes: List[Node] = Field(..., description="List of nodes in the knowledge graph")
    rels: List[Relationship] = Field(
        ..., description="List of relationships in the knowledge graph"
    )


def format_property_key(string: str) -> str:
    """Format property keys into snake case."""

    words = [word.lower() for word in string.split()]

    if not words:
        return string.lower()

    return "_".join(words)


def props_to_dict(props: list[Property]) -> dict:
    """Convert properties to a dictionary."""

    properties = {}

    if not props:
        return properties

    for prop in props:
        properties[format_property_key(prop.key)] = prop.value

    return properties


def map_to_base_node(node: Node) -> BaseNode:
    """Map the KnowledgeGraph Node to the base Node."""

    properties = props_to_dict(node.properties) if node.properties else {}
    # Add name property for better Cypher statement generation
    properties["name"] = node.id.title()

    return BaseNode(
        id=node.id.title(), type=node.type.capitalize(), properties=properties
    )


def map_to_base_relationship(rel: Relationship) -> BaseRelationship:
    """Map the KnowledgeGraph Relationship to the base Relationship."""

    source = map_to_base_node(rel.source)
    target = map_to_base_node(rel.target)
    properties = props_to_dict(rel.properties) if rel.properties else {}

    return BaseRelationship(
        source=source, target=target, type=rel.type, properties=properties
    )


def get_extraction_chain(
    llm: ChatOpenAI,
    allowed_nodes: Optional[List[str]] = None,
    allowed_rels: Optional[List[str]] = None,
    verbose: bool = False,
):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""# Knowledge Graph Instructions for GPT
## 1. Overview
You are a top-tier algorithm designed for extracting information from markdown notes in structured formats to build a knowledge graph.
- **Nodes** represent entities and concepts. They're akin to Wikipedia nodes.
- The aim is to achieve simplicity and clarity in the knowledge graph, making it accessible for a vast audience.
## 2. Labeling Nodes
- **Consistency**: Ensure you use basic or elementary types for node labels.
  - For example, when you identify an entity representing a person, always label it as **"person"**. Avoid using more specific terms like "mathematician" or "scientist".
- **Node IDs**: Never utilize integers as node IDs. Node IDs should be names or human-readable identifiers found in the text.
{'- **Allowed Node Labels:**' + ", ".join(allowed_nodes) if allowed_nodes else ""}
{'- **Allowed Relationship Types**:' + ", ".join(allowed_rels) if allowed_rels else ""}
## 3. Handling Numerical Data and Dates
- Numerical data, like age or other related information, should be incorporated as attributes or properties of the respective nodes.
- **No Separate Nodes for Dates/Numbers**: Do not create separate nodes for dates or numerical values. Always attach them as attributes or properties of nodes.
- **Property Format**: Properties must be in a key-value format.
- **Quotation Marks**: Never use escaped single or double quotes within property values.
- **Naming Convention**: Use camelCase for property keys, e.g., `birthDate`.
## 4. Coreference Resolution
- **Maintain Entity Consistency**: When extracting entities, it's vital to ensure consistency.
If an entity, such as "John Doe", is mentioned multiple times in the text but is referred to by different names or pronouns (e.g., "Joe", "he"),
always use the most complete identifier for that entity throughout the knowledge graph. In this example, use "John Doe" as the entity ID.
Remember, the knowledge graph should be coherent and easily understandable, so maintaining consistency in entity references is crucial.
## 5. Strict Compliance
Adhere to the rules strictly. Non-compliance will result in termination.
          """,
            ),
            (
                "human",
                "Use the given format to extract information from the following input: {input}",
            ),
            ("human", "Tip: Make sure to answer in the correct format"),
        ]
    )

    return create_structured_output_chain(KnowledgeGraph, llm, prompt, verbose=verbose)


def get_graph_connector() -> Neo4jGraph:
    """Returns a wrapper for the Neo4j database."""

    return Neo4jGraph(
        url=NEO4J_URL,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD,
    )


def delete_graph(are_you_sure: bool) -> None:
    """This will wipe all nodes & relationships from the Neo4j Graph."""

    if are_you_sure:
        get_graph_connector().query("MATCH (n) DETACH DELETE n")


def get_knowledge_graph_from_chunk(
    chunk: Document,
    llm: ChatOpenAI,
    allowed_nodes: list[str] | None = None,
    allowed_rels: list[str] | None = None,
    verbose: bool = False,
) -> KnowledgeGraph:
    """Runs the LLM function to extract a Knowledge Graph from a document chunk."""

    return get_extraction_chain(llm, allowed_nodes, allowed_rels, verbose).run(
        chunk.page_content
    )


def create_graph_document_from_note(
    file_name: str,
    llm: ChatOpenAI,
    allowed_nodes: list[str] | None = None,
    allowed_rels: list[str] | None = None,
    verbose: bool = False,
):
    file_store = file_handling.load_file_store()

    if file_store is None:
        print("Failed to retrieve file store. Exiting graph creation.")
        return

    collection = embedding_handling.get_vector_store_collection()

    chunks = embedding_handling.get_chunks_from_file_name(file_name)

    # get knowledge graph from chunks

    # convert knowledge graph into base nodes & base relationships

    # make graph node
    # type ObsidianVault

    # make note node
    # include uuid, file name
    # type ObsidianNote

    # make chunk nodes
    # include uuid, embeddings
    # type ObsidianNoteChunk

    # add relationship between graph node and note node

    # add relationships between note node and chunk nodes

    # add relationships between chunk nodes and GPT-generated nodes

    # assemble nodes & relationships into GraphDocument

    # later, graph.add_graph_documents([graph_document])
