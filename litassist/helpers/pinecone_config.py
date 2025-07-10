#!/usr/bin/env python3
"""
Module to handle Pinecone configuration and connection
"""

import pinecone
import requests


class PineconeWrapper:
    """Wrapper class to handle Pinecone operations using direct API calls"""

    def __init__(self, api_key, index_name):
        self.api_key = api_key
        self.index_name = index_name
        self.host = f"https://{index_name}-g2m2vyy.svc.aped-4627-b74a.pinecone.io"
        self.headers = {"Api-Key": self.api_key, "Content-Type": "application/json"}

    def describe_index_stats(self):
        """Get index statistics"""
        response = requests.post(
            f"{self.host}/describe_index_stats", headers=self.headers
        )
        data = response.json()

        # Return simple object with expected attributes
        stats = type(
            "Stats",
            (),
            {
                "dimension": data.get("dimension", 1536),
                "total_vector_count": data.get("totalVectorCount", 0),
            },
        )()
        return stats

    def upsert(self, vectors, namespace=None, **kwargs):
        """Upsert vectors to the index"""
        # Convert tuples to proper format
        formatted_vectors = []
        for item in vectors:
            if isinstance(item, tuple) and len(item) >= 2:
                vec_id, vec_values = item[0], item[1]
                vec_metadata = item[2] if len(item) > 2 else {}
                formatted_vectors.append(
                    {"id": vec_id, "values": vec_values, "metadata": vec_metadata}
                )

        data = {"vectors": formatted_vectors}
        if namespace:
            data["namespace"] = namespace
        response = requests.post(
            f"{self.host}/vectors/upsert", headers=self.headers, json=data
        )
        if response.status_code != 200:
            raise Exception(f"Upsert failed: {response.status_code} - {response.text}")

        result = response.json()

        # Return simple object with expected attribute
        response_obj = type(
            "UpsertResponse",
            (),
            {"upserted_count": result.get("upsertedCount", len(formatted_vectors))},
        )()
        return response_obj

    def query(self, vector, top_k=5, include_metadata=True, **kwargs):
        """Query the index"""
        data = {
            "vector": vector,
            "topK": top_k,
            "includeMetadata": include_metadata,
        }
        if "namespace" in kwargs:
            data["namespace"] = kwargs["namespace"]
        if "filter" in kwargs:
            data["filter"] = kwargs["filter"]

        response = requests.post(f"{self.host}/query", headers=self.headers, json=data)
        if response.status_code != 200:
            raise Exception(f"Query failed: {response.status_code} - {response.text}")
        result = response.json()

        # Convert to Pinecone-like response with simple objects
        matches = []
        for match in result.get("matches", []):
            match_obj = type(
                "Match",
                (),
                {
                    "id": match.get("id"),
                    "score": match.get("score", 0),
                    "metadata": match.get("metadata", {}),
                },
            )()
            matches.append(match_obj)

        query_result = type("QueryResult", (), {"matches": matches})()
        return query_result

    def delete(self, ids, namespace=None, **kwargs):
        """Delete vectors by ID"""
        data = {"ids": ids}
        if namespace:
            data["namespace"] = namespace
        response = requests.post(
            f"{self.host}/vectors/delete", headers=self.headers, json=data
        )
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
        index.describe_index_stats()
        print("[OK] Standard Pinecone connection successful")
        return index
    except Exception:
        # Fall back to wrapper
        print("Using direct API wrapper for Pinecone")
        return PineconeWrapper(api_key, index_name)