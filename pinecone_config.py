#!/usr/bin/env python3
"""
Module to handle Pinecone configuration and connection
"""

import pinecone
import requests
import numpy as np

class PineconeWrapper:
    """Wrapper class to handle Pinecone operations using direct API calls"""
    
    def __init__(self, api_key, index_name):
        self.api_key = api_key
        self.index_name = index_name
        self.host = f"https://{index_name}-g2m2vyy.svc.aped-4627-b74a.pinecone.io"
        self.headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def describe_index_stats(self):
        """Get index statistics"""
        response = requests.post(f"{self.host}/describe_index_stats", headers=self.headers)
        data = response.json()
        
        class Stats:
            def __init__(self, data):
                self.dimension = data.get('dimension', 1536)
                self.total_vector_count = data.get('totalVectorCount', 0)
        
        return Stats(data)
    
    def upsert(self, vectors):
        """Upsert vectors to the index"""
        # Convert tuples to proper format
        formatted_vectors = []
        for item in vectors:
            if isinstance(item, tuple) and len(item) >= 2:
                vec_id, vec_values = item[0], item[1]
                vec_metadata = item[2] if len(item) > 2 else {}
                formatted_vectors.append({
                    "id": vec_id,
                    "values": vec_values,
                    "metadata": vec_metadata
                })
        
        data = {"vectors": formatted_vectors}
        response = requests.post(f"{self.host}/vectors/upsert", headers=self.headers, json=data)
        if response.status_code != 200:
            raise Exception(f"Upsert failed: {response.status_code} - {response.text}")
        return response.json()
    
    def query(self, vector, top_k=5, include_metadata=True, **kwargs):
        """Query the index"""
        data = {
            "vector": vector,
            "topK": top_k,
            "includeMetadata": include_metadata,
        }
        if "namespace" in kwargs:
            data["namespace"] = kwargs["namespace"]
        
        response = requests.post(f"{self.host}/query", headers=self.headers, json=data)
        result = response.json()
        
        # Convert to Pinecone-like response
        class QueryResult:
            def __init__(self, data):
                self.matches = []
                for match in data.get("matches", []):
                    self.matches.append(type('Match', (), {
                        'id': match.get('id'),
                        'score': match.get('score', 0),
                        'metadata': match.get('metadata', {})
                    })())
        
        return QueryResult(result)
    
    def delete(self, ids):
        """Delete vectors by ID"""
        data = {"ids": ids}
        response = requests.post(f"{self.host}/vectors/delete", headers=self.headers, json=data)
        return response.json()


def get_pinecone_client(api_key, environment, index_name):
    """
    Get a Pinecone client that works with the current setup
    """
    try:
        # Try standard initialization
        pinecone.init(api_key=api_key, environment=environment)
        index = pinecone.Index(index_name)
        # Test if it works
        stats = index.describe_index_stats()
        print(f"✓ Standard Pinecone connection successful")
        return index
    except:
        # Fall back to wrapper
        print(f"Using direct API wrapper for Pinecone")
        return PineconeWrapper(api_key, index_name)