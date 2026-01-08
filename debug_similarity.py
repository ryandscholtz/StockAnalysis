#!/usr/bin/env python3
"""Debug script for document similarity"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.ai.document_similarity import DocumentSimilarityService

def debug_similarity():
    document = """
    Apple Inc. Financial Report 2023
    Revenue: $394.3 billion
    Net Income: $97.0 billion
    Gross Margin: 44.1%
    Operating Margin: 29.8%
    """
    
    service = DocumentSimilarityService()
    
    # Test with single document corpus
    print("=== Single document corpus ===")
    tfidf_single = service._calculate_tf_idf(document, [document])
    print(f"TF-IDF single: {list(tfidf_single.values())[:5]}")
    
    # Test with duplicate document corpus
    print("=== Duplicate document corpus ===")
    tfidf_double = service._calculate_tf_idf(document, [document, document])
    print(f"TF-IDF double: {list(tfidf_double.values())[:5]}")
    
    # Test embeddings
    print("=== Embeddings ===")
    embedding_single = service._get_tfidf_embedding(document, [document])
    embedding_double = service._get_tfidf_embedding(document, [document, document])
    
    print(f"Embedding single sum: {sum(embedding_single)}")
    print(f"Embedding double sum: {sum(embedding_double)}")
    
    # Test similarity
    similarity = service.calculate_similarity(document, document)
    print(f"Final similarity: {similarity}")

if __name__ == "__main__":
    debug_similarity()