from app.db.session import SessionDep


class VacancyRepository:
    def __init__(self, session: SessionDep):
        self._session = session

