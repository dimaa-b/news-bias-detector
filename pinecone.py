from pinecone import Pinecone, ServerlessSpec
from .env.example import PINECONE_API_TOKEN

pc = Pinecone(api_key = PINECONE_API_TOKEN )