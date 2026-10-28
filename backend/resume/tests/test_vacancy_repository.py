import unittest
import uuid
from unittest.mock import AsyncMock, Mock

from app.models.vacancy import Vacancy
from app.repositories.vacancy import VacancyRepository


class VacancyRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_saved_embedding(self):
        vacancy = Vacancy(
            id=uuid.uuid4(), user_id=uuid.uuid4(), text="Python developer",
            embedding=[0.1, -0.2],
        )
        result = Mock()
        result.scalar_one_or_none.return_value = vacancy
        result.scalars.return_value.all.return_value = [vacancy]
        session = AsyncMock()
        session.execute.return_value = result
        repository = VacancyRepository(session)

        document = await repository.get_by_id(vacancy.id)
        documents = await repository.get_by_user_id(vacancy.user_id)

        self.assertEqual(document.model_dump().get("embedding"), [0.1, -0.2])
        self.assertEqual(documents[0].model_dump().get("embedding"), [0.1, -0.2])


if __name__ == "__main__":
    unittest.main()
