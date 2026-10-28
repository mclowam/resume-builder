from app.interfaces.embedding import IEmbeddingClient
from app.schemas.event import Event
from app.schemas.pipeline import DocumentEmbedding
from app.services.document import DocumentService


class PipelineService:
    def __init__(
            self,
            document_service: DocumentService,
            embedding_client: IEmbeddingClient,
    ):
        self._document_service = document_service
        self._embedding_client = embedding_client

    async def process(self, event: Event) -> DocumentEmbedding | None:
        if await self._document_service.get_embedding(event) is not None:
            return None
        document = await self._document_service.get_document(event)
        embedding = await self._embedding_client.embed(document.text)
        await self._document_service.set_embedding(document, embedding)

        return DocumentEmbedding(
            document_id=document.document_id,
            user_id=document.user_id,
            document_type=document.document_type,
            text=document.text,
            embedding=embedding,
            embedding_model=self._embedding_client.model,
        )
