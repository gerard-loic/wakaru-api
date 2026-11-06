from sqlalchemy.orm import Session

from app.crud.model import get_model
from app.exceptions import ApiError
from app.mail.service import get_mail_service
from custom.libs.mailhelper import mail_settings

TYPE_LABELS = {"comment": "Commentaire", "bug": "Bug", "remark": "Remarque"}


class FeedbackNotConfiguredError(ApiError):
    status_code = 503
    code = "feedback_not_configured"

    def __init__(self):
        super().__init__("L'envoi de remarques n'est pas disponible pour le moment.")


def send_feedback_method(db: Session, user_id: int, feedback_type: str, message: str) -> None:
    """Transmet la remarque, avec les informations de son auteur, à l'adresse
    `WAKARU_FEEDBACK_EMAIL`."""
    if not mail_settings.feedback_email:
        raise FeedbackNotConfiguredError()

    user_model = get_model("user")
    user = db.query(user_model.python_class).filter(user_model.pk_column == user_id).one()
    get_mail_service().send(
        db,
        to=mail_settings.feedback_email,
        template="feedback",
        context={
            "type_label": TYPE_LABELS[feedback_type],
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "message": message,
        },
    )
