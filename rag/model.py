from langchain_openai import OpenAIEmbeddings

if __package__:
    from . import config
else:
    import config

embedding = OpenAIEmbeddings(
    model=config.embedding_model,
    api_key=config.api_key,
    base_url=config.base_url,
    check_embedding_ctx_length=False,
    encoding_format="float",
)
