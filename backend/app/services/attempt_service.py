from uuid import UUID

from sqlalchemy.orm import Session

from app.models import User
from app.repositories import quiz_repository
from app.services.errors import BadRequestError
from app.services.quiz_service import get_quiz, present
from app.services.transactions import transaction


def publish(db: Session, quiz_id: UUID, user: User):
    quiz = get_quiz(db, quiz_id, user, lock=True)
    if quiz.status != "draft":
        raise BadRequestError("Only a draft can be published")
    questions = quiz_repository.questions(db, quiz.id)
    options = quiz_repository.options(db, quiz.id)
    if not questions:
        raise BadRequestError("Quiz must have at least one question")
    for question in questions:
        choices = [option for option in options if option.question_id == question.id]
        if len(choices) < 2 or sum(option.is_correct for option in choices) != 1:
            raise BadRequestError(
                "Every question needs two options and one correct answer"
            )
    with transaction(db):
        quiz.status = "published"
        quiz_repository.save(db, quiz)
        result = present(db, quiz, user)
        return result
