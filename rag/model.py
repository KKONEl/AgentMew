from langchain_openai import OpenAIEmbeddings

import config

embedding = OpenAIEmbeddings(
    model=config.embedding_model,
    api_key=config.api_key,
    base_url=config.base_url,
    check_embedding_ctx_length=False,
    encoding_format="float",
)